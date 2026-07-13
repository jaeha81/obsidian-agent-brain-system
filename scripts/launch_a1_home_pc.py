# OCI A1.Flex 인스턴스 생성 재시도 스크립트 (API 방식)
# - ~/.oci/config 의 DEFAULT 프로파일 사용
# - 네트워크(VCN/서브넷/IGW/라우트)는 이름으로 조회 후 없으면 생성 (멱등)
# - Out of capacity 시 지정 간격으로 재시도
# - 성공 시 인스턴스 OCID/상태/공인 IP 출력
import sys
import time

import oci

RETRY_INTERVAL_SEC = 120
MAX_ATTEMPTS = 720  # 2분 간격 x 720 = 24시간

VCN_NAME = "vcn-bucky"
SUBNET_NAME = "subnet-bucky-public"
IGW_NAME = "igw-bucky"
VCN_CIDR = "10.0.0.0/16"
SUBNET_CIDR = "10.0.0.0/24"
INSTANCE_NAME = "bucky-a1"
OCPUS = 2
MEMORY_GB = 12
SSH_PUB_KEY_PATH = r"C:\Users\info\Downloads\ssh-key-2026-07-01.key.pub"


def log(msg):
    print(time.strftime("%H:%M:%S"), msg, flush=True)


def main():
    config = oci.config.from_file()
    tenancy = config["tenancy"]
    identity = oci.identity.IdentityClient(config, region="ap-tokyo-1")
    vnet = oci.core.VirtualNetworkClient(config, region="ap-tokyo-1")
    compute = oci.core.ComputeClient(config, region="ap-tokyo-1")

    ad = identity.list_availability_domains(tenancy).data[0].name
    log(f"AD: {ad}")

    # --- VCN (이름 조회 → 없으면 생성) ---
    vcns = vnet.list_vcns(tenancy, display_name=VCN_NAME).data
    if vcns:
        vcn = vcns[0]
        log(f"VCN 재사용: {vcn.id}")
    else:
        vcn = vnet.create_vcn(oci.core.models.CreateVcnDetails(
            compartment_id=tenancy, display_name=VCN_NAME, cidr_block=VCN_CIDR,
        )).data
        oci.wait_until(vnet, vnet.get_vcn(vcn.id), "lifecycle_state", "AVAILABLE")
        log(f"VCN 생성: {vcn.id}")

    # --- Internet Gateway ---
    igws = vnet.list_internet_gateways(tenancy, vcn_id=vcn.id).data
    if igws:
        igw = igws[0]
        log(f"IGW 재사용: {igw.id}")
    else:
        igw = vnet.create_internet_gateway(oci.core.models.CreateInternetGatewayDetails(
            compartment_id=tenancy, vcn_id=vcn.id, display_name=IGW_NAME, is_enabled=True,
        )).data
        oci.wait_until(vnet, vnet.get_internet_gateway(igw.id), "lifecycle_state", "AVAILABLE")
        log(f"IGW 생성: {igw.id}")

    # --- 기본 라우트 테이블에 0.0.0.0/0 → IGW ---
    rt = vnet.get_route_table(vcn.default_route_table_id).data
    if not any(r.destination == "0.0.0.0/0" for r in rt.route_rules):
        rules = list(rt.route_rules) + [oci.core.models.RouteRule(
            destination="0.0.0.0/0", destination_type="CIDR_BLOCK", network_entity_id=igw.id,
        )]
        vnet.update_route_table(rt.id, oci.core.models.UpdateRouteTableDetails(route_rules=rules))
        log("라우트 0.0.0.0/0 → IGW 추가")
    else:
        log("라우트 0.0.0.0/0 이미 존재")

    # --- 퍼블릭 서브넷 ---
    subnets = vnet.list_subnets(tenancy, vcn_id=vcn.id, display_name=SUBNET_NAME).data
    if subnets:
        subnet = subnets[0]
        log(f"서브넷 재사용: {subnet.id}")
    else:
        subnet = vnet.create_subnet(oci.core.models.CreateSubnetDetails(
            compartment_id=tenancy, vcn_id=vcn.id, display_name=SUBNET_NAME,
            cidr_block=SUBNET_CIDR, prohibit_public_ip_on_vnic=False,
        )).data
        oci.wait_until(vnet, vnet.get_subnet(subnet.id), "lifecycle_state", "AVAILABLE")
        log(f"서브넷 생성: {subnet.id}")

    # --- Ubuntu 24.04 aarch64 이미지 ---
    images = compute.list_images(
        tenancy, operating_system="Canonical Ubuntu", operating_system_version="24.04",
        shape="VM.Standard.A1.Flex", sort_by="TIMECREATED", sort_order="DESC",
    ).data
    if not images:
        log("Ubuntu 24.04 이미지 없음 — 중단")
        sys.exit(1)
    image = images[0]
    log(f"이미지: {image.display_name} {image.id}")

    with open(SSH_PUB_KEY_PATH, encoding="utf-8") as f:
        ssh_pub = f.read().strip()

    # --- 기존 동일 이름 인스턴스 확인 (중복 생성 방지) ---
    existing = [i for i in compute.list_instances(tenancy, display_name=INSTANCE_NAME).data
                if i.lifecycle_state not in ("TERMINATED", "TERMINATING")]
    if existing:
        log(f"이미 존재: {existing[0].id} state={existing[0].lifecycle_state} — 생성 건너뜀")
        sys.exit(0)

    details = oci.core.models.LaunchInstanceDetails(
        compartment_id=tenancy, availability_domain=ad, display_name=INSTANCE_NAME,
        shape="VM.Standard.A1.Flex",
        shape_config=oci.core.models.LaunchInstanceShapeConfigDetails(
            ocpus=OCPUS, memory_in_gbs=MEMORY_GB),
        source_details=oci.core.models.InstanceSourceViaImageDetails(image_id=image.id),
        create_vnic_details=oci.core.models.CreateVnicDetails(
            subnet_id=subnet.id, assign_public_ip=True),
        metadata={"ssh_authorized_keys": ssh_pub},
    )

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            inst = compute.launch_instance(details).data
            log(f"생성 요청 성공 (attempt {attempt}): {inst.id}")
            oci.wait_until(compute, compute.get_instance(inst.id), "lifecycle_state", "RUNNING",
                           max_wait_seconds=900)
            log("상태: RUNNING")
            vnics = compute.list_vnic_attachments(tenancy, instance_id=inst.id).data
            vnic = vnet.get_vnic(vnics[0].vnic_id).data
            log(f"PUBLIC_IP: {vnic.public_ip}  PRIVATE_IP: {vnic.private_ip}")
            return
        except oci.exceptions.ServiceError as e:
            if e.status == 500 and "capacity" in (e.message or "").lower():
                log(f"attempt {attempt}: CAPACITY_FAIL — {RETRY_INTERVAL_SEC}초 후 재시도")
                time.sleep(RETRY_INTERVAL_SEC)
            elif e.status == 429:
                log(f"attempt {attempt}: RATE_LIMITED — 300초 대기")
                time.sleep(300)
            else:
                log(f"attempt {attempt}: 예상외 오류 {e.status} {e.code}: {e.message}")
                sys.exit(1)
        except (oci.exceptions.RequestException, ConnectionError, OSError) as e:
            log(f"attempt {attempt}: NETWORK_FAIL — {type(e).__name__}: {e} — {RETRY_INTERVAL_SEC}초 후 재시도")
            time.sleep(RETRY_INTERVAL_SEC)
    log("최대 시도 횟수 도달 — 실패")
    sys.exit(1)


if __name__ == "__main__":
    main()
