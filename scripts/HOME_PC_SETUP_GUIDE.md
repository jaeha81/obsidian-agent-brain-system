# 집 PC에서 OCI 루프 이관 가이드

집 PC에서 다음 5개 Step을 순서대로 수행하세요.

---

## **Step 1: launch_a1.py 다운로드 및 저장**

Google Drive에서 파일 다운로드:
- **경로**: G:\내 드라이브\obsidian-agent-brain-system\scripts\launch_a1_home_pc.py
- **저장처**: D:\옵시디언브레인시스템\launch_a1.py

### PowerShell 확인
```powershell
Test-Path "D:\옵시디언브레인시스템\launch_a1.py"  # True 출력되어야 함
```

---

## **Step 2: OCI API 키 생성 및 config 파일 저장**

⚠️ **노트북의 API 키를 Google Drive로 복사하지 마세요. 새로 생성하세요.**

### 2-1. OCI 콘솔에서 새 API 키 생성
1. https://cloud.oracle.com 로그인 → 홈 리전을 **도쿄(ap-tokyo-1)**로 설정
2. 우상단 프로필 아이콘 → **My profile**
3. 좌측 메뉴 **API keys** → **Add API key** 클릭
4. **Generate API key pair** 선택 → **다운로드** (PrivateKey.pem)
5. **Add** 클릭

### 2-2. OCI config 파일 생성
콘솔이 보여주는 "Configuration file preview"를 복사하여 다음 경로에 저장:

**경로**: `C:\Users\{username}\.oci\config`

### config 파일 형식
Google Drive의 OCI_HOME_PC_CONFIG_TEMPLATE.ini를 참고하되, 콘솔에서 제공하는 실제 값으로 채우세요:
```ini
[DEFAULT]
user=ocid1.user.oc1..aaaaaaaaXXXXXXXXXXXXX
fingerprint=aa:bb:cc:dd:ee:ff:00:11:22:33:44:55:66:77:88:99
tenancy=ocid1.tenancy.oc1..aaaaaaaaXXXXXXXXXXXXX
region=ap-tokyo-1
key_file=C:\Users\{username}\.oci\PrivateKey.pem
```

### 2-3. 다운로드한 PrivateKey.pem 이동
- **다운로드한 위치**: C:\Users\{username}\Downloads\PrivateKey.pem
- **이동 경로**: C:\Users\{username}\.oci\PrivateKey.pem
- (.oci 폴더가 없으면 생성)

### 2-4. 검증
```powershell
# .oci 폴더 확인
Test-Path $env:USERPROFILE\.oci

# config 파일 확인
Test-Path "$env:USERPROFILE\.oci\config"

# 개인키 확인
Test-Path "$env:USERPROFILE\.oci\PrivateKey.pem"

# Python에서 검증
python -X utf8 -c "import oci; c=oci.config.from_file(); oci.config.validate_config(c); print('CONFIG_OK', c['region'])"
```

출력: `CONFIG_OK ap-tokyo-1`

---

## **Step 3: SSH 개인키 이동 (인스턴스 접속용)**

⚠️ **Google Drive로 복사하지 마세요. USB나 물리 매체로만 이동하세요.**

### 3-1. 노트북에서 SSH 키 준비
- 개인키: `C:\Users\info\Downloads\ssh-key-2026-07-01.key`
- 공개키: `C:\Users\info\Downloads\ssh-key-2026-07-01.key.pub` — launch_a1.py가 읽는 파일이므로 개인키와 함께 이동

### 3-2. 집 PC에 저장
- **경로**: `C:\Users\{username}\.ssh\ssh-key-2026-07-01.key`

### 3-3. 또는 새 SSH 키쌍 생성 (대안)
```powershell
# 집 PC에서 직접 생성 (공개키는 launch_a1.py와 일치해야 함)
ssh-keygen -t rsa -b 4096 -f "$env:USERPROFILE\.ssh\home_pc_key" -N ""
```

### 3-4. ⚠️ launch_a1.py 공개키 경로 수정 (필수)
launch_a1.py 22번째 줄이 노트북 경로로 하드코딩되어 있어, 수정 없이 실행하면 시작 즉시 FileNotFoundError로 종료됩니다. 집 PC의 실제 공개키 경로로 수정하세요:
```python
# 수정 전 (노트북 경로)
SSH_PUB_KEY_PATH = r"C:\Users\info\Downloads\ssh-key-2026-07-01.key.pub"
# 수정 후 예시 — USB로 가져온 경우
SSH_PUB_KEY_PATH = r"C:\Users\{username}\.ssh\ssh-key-2026-07-01.key.pub"
# 수정 후 예시 — 3-3에서 새로 생성한 경우
SSH_PUB_KEY_PATH = r"C:\Users\{username}\.ssh\home_pc_key.pub"
```

---

## **Step 4: launch_a1.py 기동**

### 4-1. Python 패키지 확인
```powershell
pip show oci
# 없으면: pip install oci
```

### 4-2. 루프 시작 (백그라운드)
```powershell
Start-Process cmd.exe -ArgumentList '/c', 'python -X utf8 D:\옵시디언브레인시스템\launch_a1.py > D:\옵시디언브레인시스템\launch_a1.log 2>&1'
```

### 4-3. 즉시 검증
```powershell
# 새 Python 프로세스 확인
tasklist | findstr python

# 로그 확인 (5줄)
Get-Content "D:\옵시디언브레인시스템\launch_a1.log" -Tail 5
```

출력 예:
```
07:45:23 AD: ap-tokyo-1a
07:45:24 VCN 재사용: ocid1.vcn.oc1.ap-tokyo-1.xxxxx
07:45:24 IGW 재사용: ocid1.internetgateway.oc1.ap-tokyo-1.xxxxx
07:45:25 attempt 1: CAPACITY_FAIL — 120초 후 재시도
```

---

## **Step 5: 노트북 루프 종료 (이 Step 4가 정상 작동한 후에만)**

### 5-1. 노트북에서 현재 PID 확인
```powershell
tasklist | findstr python  # PID 확인
```

### 5-2. 노트북 루프 종료
```powershell
Stop-Process -Id <PID> -Force
```

---

## **성공 후 다음 단계**

인스턴스가 생성되어 PUBLIC_IP가 출력되면:

```powershell
ssh -i $env:USERPROFILE\.ssh\ssh-key-2026-07-01.key ubuntu@<PUBLIC_IP>
```

인스턴스 초기 설정:
```bash
sudo apt update && sudo apt install -y python3-pip python3-venv git ffmpeg
```

---

## **트러블슈팅**

### 로그가 없음
→ 백그라운드 프로세스가 바로 끝남. 다음 확인:
```powershell
tasklist | findstr python  # PID가 없으면 프로세스 사망
```

### "Cannot find drive 'D'"
→ 집 PC에서 D: 드라이브가 아직 설정되지 않음. D:\옵시디언브레인시스템\ 폴더 경로 확인.

### "CONFIG_OK" 출력 안 됨
→ .oci/config 또는 개인키 경로 오류. config 파일 재검토.

### CAPACITY_FAIL 반복
→ 정상 작동. 용량 확보 대기 중 (24시간 계속 재시도).
