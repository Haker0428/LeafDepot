/*
 * @Author: big box big box@qq.com
 * @Date: 2025-10-27 23:43:42
 * @LastEditors: big box big box@qq.com
 * @LastEditTime: 2025-10-27 23:43:46
 * @FilePath: /ui/src/hooks/taskUtils.ts
 * @Description: 
 * 
 * Copyright (c) 2025 by lizh, All Rights Reserved. 
 */
// taskUtils.ts
import { v4 as uuidv4 } from 'uuid';
import { CreateTaskGroupRequest, TaskData, TargetRoute } from './types';

export const createTaskGroupData = (): CreateTaskGroupRequest => {
    // 生成任务数据
    const taskData: TaskData[] = [
        {
            robotTaskCode: `task_001_${uuidv4().slice(0, 8)}`,
            sequence: 1
        },
        {
            robotTaskCode: `task_002_${uuidv4().slice(0, 8)}`,
            sequence: 2
        },
        {
            robotTaskCode: `task_003_${uuidv4().slice(0, 8)}`,
            sequence: 3
        }
    ];

    // 目标路由
    const targetRoute: TargetRoute = {
        type: "ZONE",
        code: "A3"
    };

    // 返回完整的任务组数据
    return {
        groupCode: `test_group_${uuidv4().slice(0, 8)}`,
        strategy: "GROUP_SEQ",
        strategyValue: "1", // 组间及组内都有序
        groupSeq: 10,
        targetRoute: targetRoute,
        data: taskData
    };
};