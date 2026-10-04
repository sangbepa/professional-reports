"""Frozen lexical retrieval; vector providers may implement the same manifest contract."""
import re
import hashlib
from pathlib import Path
from .util import ContractError, digest, hash_data, read_json, timestamp, write_json


def tokenize(text):
    return re.findall(r'[\w가-힣]+',text.lower())


def build(documents,cutoff,out,chunk_chars=1800,overlap=150):
    if not 0<=overlap<chunk_chars:raise ContractError('Invalid chunk overlap')
    chunks=[];corpus=[]
    ids=[d['id'] for d in documents]
    if len(ids)!=len(set(ids)):raise ContractError('Duplicate source identifiers in retrieval corpus')
    for d in documents:
        known=d.get('published_at')
        window=d.get('publication_window')
        if known:
            eligible=timestamp(known)<=timestamp(cutoff)
        elif window:
            start=timestamp(window['not_before']);end=timestamp(window['not_after'])
            eligible=start<=end<=timestamp(cutoff)
        else:eligible=False
        if not eligible or not d.get('publication_evidence'):
            raise ContractError('RAG corpus includes future or unverified-publication document')
        p=Path(d['path']);raw=p.read_bytes();h=hashlib.sha256(raw).hexdigest()
        if d.get('sha256',h)!=h:raise ContractError('Corpus snapshot changed')
        text=raw.decode('utf-8')
        corpus.append(dict(id=d['id'],sha256=h,published_at=known,publication_window=window,publication_evidence=d['publication_evidence']))
        for offset in range(0,len(text),chunk_chars-overlap):
            content=text[offset:offset+chunk_chars]
            chunks.append(dict(id=f"{d['id']}:{offset}",document_id=d['id'],document_sha256=h,start=offset,end=offset+len(content),text=content))
    manifest=dict(schema_version='retrieval/1',engine='lexical-overlap-v1',embedding=None,cutoff=cutoff,
                  chunking=dict(chars=chunk_chars,overlap=overlap),corpus=corpus,chunks=chunks)
    manifest['sha256']=hash_data(manifest);write_json(out,manifest)
    return manifest


def search(index,query,expected_sha256,limit=6):
    data=read_json(index);unsigned={k:v for k,v in data.items() if k!='sha256'}
    if hash_data(unsigned)!=expected_sha256 or data['sha256']!=expected_sha256:raise ContractError('Retrieval index version/hash changed')
    if limit<1:raise ContractError('Retrieval limit must be positive')
    terms=set(tokenize(query))
    ranked=sorted(((len(terms & set(tokenize(c['text']))),c) for c in data['chunks']),key=lambda x:(-x[0],x[1]['id']))
    used=[dict(c,score=s) for s,c in ranked if s>0][:limit]
    return dict(query=query,limit=limit,engine=data['engine'],index_sha256=expected_sha256,cutoff=data['cutoff'],used_chunks=used)
