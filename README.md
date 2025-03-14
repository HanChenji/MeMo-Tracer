
# MeMo: Enhancing Representative Sampling via Mechanistic Micro-Model Signatures

## What's MeMo
MeMo is the code signature proposed to enhance the performance estimatiion accuracy of representative sampling in the pre-silicon stage of microarchitecture designs.

MeMo involves various signatures sourced from a series of micro-models under different paramter configurations. 
Specifically, to categorize imperfections in µArch structures systematically, MeMo employs fetch, issue, and cache micro-models, each concentrating on certain structure constraints while idealizing the others. 
Events due to corresponding µArch constraints are utilized as the code signatures, including the fetch stall cycles, branch MPKI, and cache miss rates. 

Utilizing these events as the code signature can comprehensively portray different program characteristics and effectively correlate with program performance. 
Besides, MeMo is sourced from a series of parameterized, module-level mechanistic models rather than from a specific realistic µArch, thereby avoiding dependence on any particular µArch.

## How to Run

### Compile:
MeMo is built based on the ZSim platform, and utilizes the PIN as the trace generator. 
```shell
scons
```

Python environment setup:
```shell
pip install -r requirements.txt
```

### Demo

This repo provides a demo to profile code signatures of MeMo for STREAM.

```shell
./profile.sh | parallel -j 16
./run-MeMo.py -t concatenating -p demo-STREAM-1
```