import React from "react";
import {interpolate,spring,useCurrentFrame,useVideoConfig} from "remotion";
import type {Scene} from "../types";

export const DirectedVisual:React.FC<{scene:Scene;accentHex:string}>=({scene,accentHex})=>{
 const d=scene.visualDirection;
 if(!d||d.visualType==="presenter"||d.visualType==="screenshot"||d.visualType==="b-roll"||d.visualType==="cta") return null;
 const frame=useCurrentFrame(); const {fps}=useVideoConfig();
 const pop=spring({frame,fps,config:{damping:15,stiffness:190,mass:.7}});
 const opacity=interpolate(frame,[0,Math.max(4,Math.round(fps*.12))],[0,1],{extrapolateRight:"clamp"});
 const base:React.CSSProperties={position:"absolute",inset:0,display:"flex",alignItems:"center",justifyContent:"center",pointerEvents:"none",opacity,transform:`scale(${.78+.22*pop})`,fontFamily:'"Noto Sans CJK JP", sans-serif'};
 if(d.visualType==="symbol") return <div style={{...base,fontSize:520,fontWeight:900,color:d.symbol==="×"?"#ff453a":"#34c759",textShadow:"0 20px 70px rgba(0,0,0,.65)"}}>{d.symbol??"○"}</div>;
 if(d.visualType==="hero") return <div style={{...base,padding:"0 80px",fontSize:112,fontWeight:950,lineHeight:1.05,textAlign:"center",color:accentHex,textShadow:"0 8px 35px rgba(0,0,0,.8)"}}>{scene.caption}</div>;
 if(d.visualType==="comparison") return <div style={{...base,gap:26,padding:70}}><div style={{flex:1,padding:42,borderRadius:36,background:"rgba(255,69,58,.9)",fontSize:62,fontWeight:900}}>BEFORE</div><div style={{fontSize:86,fontWeight:900}}>→</div><div style={{flex:1,padding:42,borderRadius:36,background:"rgba(52,199,89,.9)",fontSize:62,fontWeight:900}}>AFTER</div></div>;
 if(d.visualType==="card") return <div style={{...base,padding:70}}><div style={{padding:"48px 52px",borderRadius:38,background:"rgba(255,255,255,.94)",color:"#111",fontSize:68,fontWeight:900,lineHeight:1.18,textAlign:"center",boxShadow:"0 24px 80px rgba(0,0,0,.45)"}}>{scene.caption}</div></div>;
 return null;
};
