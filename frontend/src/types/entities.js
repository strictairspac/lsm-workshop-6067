/** @typedef {{id:number,name:string,description:string,entries:Array,status:string,total_count:number|null,received_count:number,gaps:Array,segments:Array}} Dataset */
/** @typedef {{start_seq:number,count:number,content_hash:string}} DatasetSegment */
/** @typedef {{id:number,name:string,memtable_limit:number,l0_trigger:number,max_levels:number,final_compaction:boolean}} Config */
/** @typedef {{id:number,name:string,dataset_id:number,config_id:number,status:string,result:Object}} Trial */
export const entityNames={dataset:'键值批次',config:'存储配置',trial:'合并试验'};
