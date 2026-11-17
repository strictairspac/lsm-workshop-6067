import{api,post}from'./client.js';
export const list=()=>api('/datasets');
export const create=data=>post('/datasets',data);
export const detail=id=>api('/datasets/'+id);
export const addSegment=(id,data)=>post('/datasets/'+id+'/segments',data);
export const seal=id=>post('/datasets/'+id+'/seal',{});
