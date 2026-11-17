"use client";
import {useEffect,useState} from "react";
import RectangleTool from "../RectangleTool";
import ReplaceText from "./ReplaceText";
import ParagraphEditor from "./ParagraphEditor";
export default function Page(){const [mode,setMode]=useState("replace"),[ready,setReady]=useState(false);useEffect(()=>setReady(true),[]);return <><div style={{textAlign:"center",padding:"12px 20px"}}><label>편집 방식 <select disabled={!ready} value={mode} onChange={e=>setMode(e.target.value)}><option value="replace">기존 글자 직접 수정</option><option value="paragraph">문단 재배치 · 글꼴 보존</option><option value="add">새 글자 추가</option></select></label></div>{mode==="replace"?<ReplaceText/>:mode==="paragraph"?<ParagraphEditor/>:<RectangleTool/>}</>;}
