/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-27 23:43:09
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-10-27 23:43:13
 * @FilePath: /ui/src/hooks/types.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by lizh, All Rights Reserved. 
 */
// types.ts
export interface TaskData {
    robotTaskCode: string;
    sequence: number;
}

export interface TargetRoute {
    type: string;
    code: string;
}

export interface CreateTaskGroupRequest {
    groupCode: string;
    strategy: string;
    strategyValue?: string;
    groupSeq?: number;
    targetRoute?: TargetRoute;
    data: TaskData[];
}

export interface ApiResponse {
    code: string;
    message: string;
}