#!/usr/bin/env python3
from __future__ import annotations
import argparse, json, re
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONFIG=ROOT/"config"/"visual_director.json"

def choose_visual(scene:dict,cfg:dict,index:int)->dict:
    text=str(scene.get("caption") or scene.get("narration") or "")
    scene_type=str(scene.get("type") or "talk")
    if scene_type=="cta":
        return {"visualType":"cta","reason":"scene-type:cta","confidence":1.0}
    for rule in cfg["rules"]:
        hit=next((k for k in rule["keywords"] if k.lower() in text.lower()),None)
        if hit:
            out={"visualType":rule["visualType"],"reason":f"keyword:{hit}","confidence":0.78}
            if rule.get("symbol"): out["symbol"]=rule["symbol"]
            return out
    if re.search(r"\d+(?:\.\d+)?(?:%|％|倍|秒|分|時間|円|人)",text):
        return {"visualType":"hero","reason":"numeric-proof","confidence":0.74}
    # avoid endless presenter-only rhythm even before an AI asset selector exists
    if index>0 and index%3==2:
        return {"visualType":"card","reason":"rhythm-break","confidence":0.55}
    return {"visualType":"presenter","reason":"default","confidence":0.5}

def direct(plan:dict,cfg:dict)->dict:
    scenes=[]
    for i,scene in enumerate(plan.get("scenes") or []):
        direction=choose_visual(scene,cfg,i)
        item=dict(scene)
        item["visualDirection"]=direction
        vt=direction["visualType"]
        if vt in {"hero","symbol","card","comparison"}:
            item["layoutVariant"]="fullscreen-card" if vt in {"card","comparison"} else "center"
            item["cameraMotion"]="punch-in" if vt in {"hero","symbol"} else "slow-push"
        elif vt=="cta":
            item["cameraMotion"]="cta-push"
        scenes.append(item)
    return {"version":1,"source":"visual-director-rules-v1","durationSeconds":plan.get("durationSeconds"),"scenes":scenes}

def main()->int:
    ap=argparse.ArgumentParser()
    ap.add_argument("--scene-plan",type=Path,required=True)
    ap.add_argument("--output",type=Path)
    a=ap.parse_args()
    plan=json.loads(a.scene_plan.read_text(encoding="utf-8"))
    cfg=json.loads(CONFIG.read_text(encoding="utf-8"))
    out=direct(plan,cfg)
    dest=a.output or a.scene_plan.with_name("visual-director-plan.json")
    dest.write_text(json.dumps(out,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    counts={}
    for s in out["scenes"]:
        k=s["visualDirection"]["visualType"]; counts[k]=counts.get(k,0)+1
    print("visual-director:",", ".join(f"{k}={v}" for k,v in counts.items()))
    print(f"- plan: {dest}")
    return 0
if __name__=="__main__": raise SystemExit(main())
