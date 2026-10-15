# Sector 실패 사례와 V6 복구 분석

본실험210회의Sector 결과 중 숲 미완주2건과맵1 접촉 후 완주1건을 분석한다. 세 비행 모두 기록·자원·속도·독립solid 감사가 유효하고 실행 오류나OOM으로 분류되지 않았다. 실패를 삭제하거나 재실행 결과로 대체하지 않는다. Sector는기존 무회전 방식이 아니라 정지 후방향 회전·새 관측·맵 갱신·재계획을 수행하는 Active-Yaw Sector다.

## 실제 결과

|사례|목표 도달|접촉 주행|종료시간|확인된 종료 원인|
|---|---:|---:|---:|---|
|숲4회차 Sector|2/5|1|193.31s|실제solid 접촉 뒤60초 정체|
|숲5회차 Sector|1/5|0|154.05s|무접촉 상태에서60초 무진전|
|맵1 6회차 Sector|5/5|1|108.08s|접촉에서 벗어난 뒤 미션 완주|

완주와접촉 여부는 독립적이다. 맵1 6회차는완주에 포함되지만무접촉 완주에는 포함되지 않는다. 본실험Sector의68/70 완주,2/70 접촉 주행,67/70 무접촉 완주가 서로 다른 이유다.

세 사례의원본 artifacts 디렉터리와solid 사건은 `case_records.json`에 저장했다. 아래 stack 줄번호는 해당비행의 `artifacts/<map>_run<run>_<mode>.attempt1.stack.log`를 가리킨다. 원본파일 해시는`source_manifest.json`에 있다.

## 숲4회차 접촉 후 정체

원본: `results/topology_polyline_v6_n10_20261006/seven_map_n10/forest_cluster_f01/r04/sector/`, run99528.

20회의방향 회전과새 맵 준비 동작이 기록됐다. stack7340에서마지막yaw map-ready,7351~7356에서gen175 경로 인증·출발,7416에서gen181 맵 인증commit이 확인된다. 독립solid 감사는133.025초에`trunk_003` 접촉을검출했고,6030에가까운 수신접촉표본(정확히6029개)으로구성된1episode가종료까지이어졌다. 최종 위치는약(-17.7737,-19.5308,0.9499)m다.

gen181 commit은 접촉 약3ms 전이었고,7423의candidate clearance 거절은 접촉 약135ms 후,7437의main-pre brake 거절은 약280ms 후였다. 마지막 경로 상태는OCCUPIED였고 접촉 상태 정체가60.001초 지속되어 미완주로 종료됐다. 맵 인증과 실제solid 접촉이 일치하지 않은 현상은 확인되지만, 해당 장애물이 실제로 입력cloud에서 누락됐는지를 검증할 동기화raw cloud·ROG snapshot은 보존되지 않았다.

그림: `case_forest_r04.png`.

## 숲5회차 인증 후보가 실행되지 않은 정체

원본: `results/topology_polyline_v6_n10_completion_20261007/seven_map_n10/forest_cluster_f01/r05/sector/`, run99535.

22회의yaw map-ready와반복CIRI 회랑 실패가관측됐다. stack5262에서국소수평4/4·수직1/1 복구예산소진,5364에서episode7의네번째방향 관측과map1103 준비가기록됐다. 5370~5372에서12knot,3.521m 이동을계획한V6 다중구간후보gen61이map1103 기준으로인증·commit됐다.

그러나5373의async 결과는completed=false이고,약9.3ms 후5374에서는map1104 기준의출발검사를거절하여brake를유지했다. gen61의실제출발certificate·release는없다. commit 이후실제위치변위는0이고,약(7.0293,20.0333,2.1042)m에서60.002초정체하여종료됐다. 접촉0,최소표본body clearance0.3007m다. 이후CIRI 실패와복구소진도이어졌다.

공통출발인증은staged map과현재map의버전일치를요구한다. `super_planner.cpp`3491~3504의certificate 조회, `fsm_ros2.hpp`4335~4346의현재map 재검증과4393~4406의조건부출발에서이계약을확인했다. map1103에서1104로바뀐것만으로도해당후보의출발허가를거절할수있다. `not_attempted`는출발결과구조체의기본문자열이지기하학적경로검색실패의진단명이아니다.

또한 `certified_polyline_recovery.cpp`15·28의episode당1회예산은검색전에소비되고, `super_planner.cpp`2896의재설정에는새목표나2m이상수평진행이필요하다. 출발하지못한후보가예산을소비한채정체한상태여서동일episode의두번째polyline 시도는없었다. 이는안전확인을낮추지않는freshness 정책과공통복구예산이결합된진행성민감도다. 새안전버그가입증된것은아니지만,순수한시야제한만을유일한원인으로설명할수도없다.

허용되는설명은“Active-Yaw Sector에서도반복방향관측과맵갱신후완주하지못한사례가있었다”이다. “어떤기하학적우회경로도존재하지않았다”나“모든공통진행성결함이해결됐다”는표현은근거가없다. 사용자요청대로이번동결에서는코드를수정하지않고이결과와해석한계를보존한다.

그림: `case_forest_r05.png`.

## 맵1 접촉 후 완주

원본: `results/topology_polyline_v6_n10_completion_20261007/seven_map_n10/gapfree_d1_m01/r06/sector/`, run99536.

독립solid 접촉은44.023~44.212초의`cylinder_0223`에대한19개수신표본,1episode다. stack2734~2739에서gen88 인증·출발,2868에서접촉약111ms 전gen96 commit이있다. 2897의main-pre brake 거절은접촉약431ms 후이며last_path_status=UNOBSERVED다. 2913~2915에서인증정지와새yaw 관측을수행했고이후5/5 목표에도착했다. 총19회의yaw map-ready 중8회가접촉전에발생했다.

이사례는“접촉하면반드시미완주한다”는가정이틀림을보여준다. 여기서도특정장애물의실제관측누락을재구성할raw cloud나yaw가포함된odometry는없으므로,입력시야와접촉사이의배타적인인과관계를확정하지않는다.

그림: `case_map1_r06.png`.

## Full에서 실제 복구 후 진행 재개

원본: `results/topology_polyline_v6_n10_20261006/seven_map_n10/forest_cluster_f01/r03/full/`, run99521.

stack2940에서astar_no_path와기존복구소진,2961~2963에서9knot·4.166m V6 후보와gen70/map398 commit,2964~2970에서출발certificate·release 및completed=true를확인했다. 출발약12.66초후다음목표를받았고그시점까지위치는14.516m 진행했다. 그구간의최소표본body clearance는0.2702m다. 비행전체8029개수신표본의독립감사에서접촉0·최소여유0.2552m이며80.30초에전체미션을완주했다.

이는새복구분기가실제진행을재개한사례지만,내부맵이저장되지않은과거run97036의정확한실패상태재생은아니다. 일반본실험에서V6 polyline commit은이Full 1회와숲5회차Sector 1회뿐이며,Adaptive에서는0회였다. Adaptive의좋은결과를V6 polyline branch의발동효과로설명하지않는다.

그림: `case_forest_r03.png`.

## Adaptive의 실제 전환 확인

본실험Adaptive70회에는509개의Full 열기→실제Full 획득frame→맵ACK→새경로인증·출발→Sector 복귀가있다. 별도숲사전시험10회의109개전환은합산하지않는다. 독립로그감사는cycle·request sequence·센서stamp·map identity와시간순서,증가한경로generation,committed=1·planner_release=1을확인했으며불일치나미복귀cycle은없었다.

대표적으로숲5회차Adaptive stack1337의Full 요청,1339의실제Full frame113,1344~1345의map113 ACK,1388~1391의gen28/map127 경로인증·출발,1395의Sector 복귀와1397의새sector 획득frame을확인했다. 결과는`adaptive_contract_audit.json`에저장했다.

## 논문 해석 범위

현재자료는동일한공통planner 버전에서관측방식을달리한7개정적시뮬레이션맵의반복실험이다. Sector 조합에서관측된접촉·미완주·긴주행시간을그평가조건의성능한계로보고하고,Adaptive가해당평가에서무접촉완주와처리비용감소를동시에유지했다는사용동기를제시할수있다.

시야만을원인으로격리한실험,실기체검증,모집단100% 보장,연속swept-volume 인증,통계적으로확정된안전성우위는아니다. 무진전60초종료가있으므로Sector가무한시간에도완주할수없다고주장하지않는다. 맵freshness와복구예산의공통진행성민감도는별도한계로남기며,실패결과는동결본에서그대로유지한다.
