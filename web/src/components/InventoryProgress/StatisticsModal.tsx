import { motion } from "framer-motion";

interface AbnormalTask {
  taskNo: string;
  location: string;
  expected: number;
  actual: number;
}

interface StatisticsData {
  totalTime: number;
  diffRate: number;
  abnormalTasks: AbnormalTask[];
}

interface Props {
  statisticsData: StatisticsData;
  inventoryItemsLength: number;
  setIsStatisticsModalOpen: (open: boolean) => void;
  pendingSaveAction: (() => void) | null;
  setPendingSaveAction: (action: (() => void) | null) => void;
  formatTime: (milliseconds: number) => string;
}

export default function StatisticsModal({
  statisticsData,
  inventoryItemsLength,
  setIsStatisticsModalOpen,
  pendingSaveAction,
  setPendingSaveAction,
  formatTime,
}: Props) {
  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <motion.div
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        className="bg-white rounded-xl shadow-2xl max-w-2xl w-full mx-4"
      >
        {/* 模态框头部 */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h3 className="text-2xl font-bold text-green-800 flex items-center">
              <i className="fa-solid fa-chart-pie mr-3 text-green-600"></i>
              盘点结果统计
            </h3>
            <button
              onClick={() => setIsStatisticsModalOpen(false)}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <i className="fa-solid fa-times text-xl"></i>
            </button>
          </div>
        </div>

        {/* 模态框内容 */}
        <div className="p-6">
          {/* 统计概览 */}
          <div className="grid grid-cols-3 gap-4 mb-6">
            <div className="bg-blue-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-blue-700">
                {formatTime(statisticsData.totalTime)}
              </div>
              <div className="text-sm text-blue-600 mt-1">总耗时</div>
            </div>
            <div className={`rounded-lg p-4 text-center ${statisticsData.diffRate <= 10 ? "bg-green-50" : statisticsData.diffRate <= 50 ? "bg-yellow-50" : "bg-red-50"}`}>
              <div className={`text-2xl font-bold ${statisticsData.diffRate <= 10 ? "text-green-700" : statisticsData.diffRate <= 50 ? "text-yellow-700" : "text-red-700"}`}>
                {statisticsData.diffRate.toFixed(1)}%
              </div>
              <div className={`text-sm mt-1 ${statisticsData.diffRate <= 10 ? "text-green-600" : statisticsData.diffRate <= 50 ? "text-yellow-600" : "text-red-600"}`}>差异率</div>
            </div>
            <div className="bg-red-50 rounded-lg p-4 text-center">
              <div className="text-2xl font-bold text-red-700">
                {statisticsData.abnormalTasks.length}
              </div>
              <div className="text-sm text-red-600 mt-1">差异任务</div>
            </div>
          </div>

          {/* 差异任务列表 */}
          {statisticsData.abnormalTasks.length > 0 ? (
            <div className="border border-gray-200 rounded-lg overflow-hidden">
              <div className="bg-gray-50 px-4 py-3 border-b border-gray-200">
                <h4 className="font-semibold text-gray-800 flex items-center">
                  <i className="fa-solid fa-exclamation-triangle text-orange-500 mr-2"></i>
                  差异任务详情
                </h4>
              </div>
              <div className="max-h-60 overflow-y-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-100">
                    <tr>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">任务编号</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">库位</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">系统数量</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">实际数量</th>
                      <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase">差异</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {statisticsData.abnormalTasks.map((task, index) => (
                      <tr key={index} className="hover:bg-red-50 transition-colors">
                        <td className="px-4 py-2 text-sm font-medium text-gray-900">{task.taskNo}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{task.location}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{task.expected}</td>
                        <td className="px-4 py-2 text-sm text-gray-700">{task.actual}</td>
                        <td className="px-4 py-2 text-sm font-medium text-red-600">
                          {task.actual - task.expected > 0 ? "+" : ""}{task.actual - task.expected}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : (
            <div className="text-center py-8 border border-gray-200 rounded-lg bg-green-50">
              <i className="fa-solid fa-check-circle text-green-500 text-4xl mb-3"></i>
              <h4 className="text-lg font-medium text-green-800 mb-2">盘点结果完美</h4>
              <p className="text-green-600">所有任务均无差异</p>
            </div>
          )}

          {/* 总结信息 */}
          <div className="mt-6 p-4 bg-gray-50 rounded-lg">
            <div className="flex justify-between items-center">
              <div>
                <h5 className="font-semibold text-gray-800">盘点总结</h5>
                <p className="text-sm text-gray-600">
                  共完成 {inventoryItemsLength} 个盘点任务
                  {statisticsData.abnormalTasks.length > 0 && `，其中 ${statisticsData.abnormalTasks.length} 个任务存在差异`}
                </p>
              </div>
              <div className="text-right">
                <div className={`text-lg font-bold ${
                  statisticsData.diffRate <= 10 ? "text-green-600"
                    : statisticsData.diffRate <= 50 ? "text-yellow-600"
                    : "text-red-600"
                }`}>
                  总体评价:{" "}
                  {statisticsData.diffRate <= 10 ? "正常"
                    : statisticsData.diffRate <= 50 ? "偏差较大"
                    : "严重异常"}
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 模态框底部 */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 flex justify-end gap-3">
          {pendingSaveAction ? (
            <>
              <button
                onClick={() => {
                  setIsStatisticsModalOpen(false);
                  setPendingSaveAction(null);
                }}
                className="bg-gray-400 hover:bg-gray-500 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
              >
                <i className="fa-solid fa-arrow-left mr-2"></i>返回
              </button>
              <button
                onClick={() => {
                  setIsStatisticsModalOpen(false);
                  setPendingSaveAction(null);
                  pendingSaveAction();
                }}
                className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
              >
                <i className="fa-solid fa-check mr-2"></i>确认
              </button>
            </>
          ) : (
            <button
              onClick={() => setIsStatisticsModalOpen(false)}
              className="bg-green-600 hover:bg-green-700 text-white px-6 py-2 rounded-lg transition-colors flex items-center"
            >
              <i className="fa-solid fa-check mr-2"></i>确认
            </button>
          )}
        </div>
      </motion.div>
    </div>
  );
}
