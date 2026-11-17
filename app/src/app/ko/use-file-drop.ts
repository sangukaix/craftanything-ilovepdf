"use client";
import {useEffect, useRef, useState} from "react";

// Listen on the window so files dropped on whitespace, the header or footer are handled too.
export function useFileDrop(receive:(files:File[])=>void, busy:boolean) {
  const latest=useRef({receive,busy});
  latest.current={receive,busy};
  const [dragging,setDragging]=useState(false);
  useEffect(()=>{
    let depth=0;
    const isFile=(e:DragEvent)=>Boolean(e.dataTransfer && (Array.from(e.dataTransfer.types||[]).includes("Files") || e.dataTransfer.files.length || Array.from(e.dataTransfer.items||[]).some(i=>i.kind==="file")));
    const enter=(e:DragEvent)=>{if(!isFile(e))return;e.preventDefault();depth++;if(!latest.current.busy)setDragging(true);};
    const over=(e:DragEvent)=>{if(!isFile(e))return;e.preventDefault();if(e.dataTransfer)e.dataTransfer.dropEffect=latest.current.busy?"none":"copy";};
    const leave=()=>{depth=Math.max(0,depth-1);if(!depth)setDragging(false);};
    const reset=()=>{depth=0;setDragging(false);};
    const drop=(e:DragEvent)=>{
      if(!isFile(e))return;e.preventDefault();reset();
      if(latest.current.busy)return;
      let files=Array.from(e.dataTransfer?.files||[]);
      if(!files.length)files=Array.from(e.dataTransfer?.items||[]).map(i=>i.kind==="file"?i.getAsFile():null).filter((f):f is File=>Boolean(f));
      latest.current.receive(files);
    };
    window.addEventListener("dragenter",enter,true);window.addEventListener("dragover",over,true);window.addEventListener("dragleave",leave,true);window.addEventListener("drop",drop,true);window.addEventListener("blur",reset);
    return ()=>{window.removeEventListener("dragenter",enter,true);window.removeEventListener("dragover",over,true);window.removeEventListener("dragleave",leave,true);window.removeEventListener("drop",drop,true);window.removeEventListener("blur",reset);};
  },[]);
  return dragging;
}
