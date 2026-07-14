# -*- coding: utf-8 -*-
"""F1 MAML 프로토타입 (신규 모듈, 기존 파일 무수정).

tasks.py   : 페르소나 스윕 → 가상 사용자 태스크(support/query) 생성
distill.py : numpy MLP(7→32→16→2) + 룰(compute_e1_e2) 지식증류 사전학습
adapt.py   : inner loop — support 30분 3-step 경사하강 적응
fomaml.py  : outer loop — FOMAML로 공통 초기점 θ 메타학습
run_demo.py: 적응 전/후 비교표 출력 + results.json 저장
"""
