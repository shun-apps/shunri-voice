#!/usr/bin/env python3
from visual_director import direct
CFG={"rules":[
 {"visualType":"symbol","symbol":"×","keywords":["問題"]},
 {"visualType":"screenshot","keywords":["画面","Canva"]},
 {"visualType":"hero","keywords":["AI"]}
]}
plan={"durationSeconds":6,"scenes":[
 {"id":"s1","caption":"この問題です","type":"talk"},
 {"id":"s2","caption":"Canvaを開きました","type":"talk"},
 {"id":"s3","caption":"普通の説明です","type":"talk"},
 {"id":"s4","caption":"詳しくはこちら","type":"cta"}
]}
out=direct(plan,CFG)
assert [x["visualDirection"]["visualType"] for x in out["scenes"]]==["symbol","screenshot","card","cta"]
assert out["scenes"][0]["visualDirection"]["symbol"]=="×"
assert out["scenes"][1]["visualDirection"]["reason"]=="keyword:Canva"
assert out["scenes"][0]["cameraMotion"]=="micro-drift"
print("visual-director-self-test: OK")
