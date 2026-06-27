# Test Fixtures

실데이터 fixture는 이 디렉토리에 넣지 않는다. 익명화된 mock 데이터만 허용.

실제 견적서(.xlsx) 파일, 실제 단가, 협력사 정보, 프로젝트명이 포함된 파일은
절대 이 디렉토리에 커밋하지 않는다.

테스트용 fixture가 필요한 경우:
- 테스트 코드 내 Python dict/list로 직접 정의 (inline mock data)
- 또는 익명화된 가상 데이터를 `mock_*.xlsx` 등으로 저장 (gitignore 추가 권장)
