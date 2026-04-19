import { useState, useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { GATEWAY_URL } from "../config/ip_address";
import { useAuth } from "../contexts/authContext";

interface InventoryDetail {
  序号: number;
  品规名称: string;
  储位名称: string;
  实际品规: string;
  库存数量: number;
  实际数量: number;
  差异: string;
  修改记录: string;
  照片1路径: string;
  照片2路径: string;
  照片3路径: string;
  照片4路径: string;
}

interface TaskMeta {
  operator: string;
  hasModified: boolean;
  modifiedBins: string[];
  taskDate: string;
  isValid: boolean;
}

export default function HistoryDetail() {
  const { taskId } = useParams<{ taskId: string }>();
  const navigate = useNavigate();
  const { userLevel, userName } = useAuth();
  const [taskDetails, setTaskDetails] = useState<InventoryDetail[]>([]);
  const [taskMeta, setTaskMeta] = useState<TaskMeta>({ operator: "", hasModified: false, modifiedBins: [], taskDate: "", isValid: true });
  const [loading, setLoading] = useState(true);
  const [selectedBin, setSelectedBin] = useState<InventoryDetail | null>(null);
  const [photoUrls, setPhotoUrls] = useState<string[]>([]);
  const [selectedPhotoIdx, setSelectedPhotoIdx] = useState(0);
  const [mainImgError, setMainImgError] = useState(false);
  const [failedThumbIdx, setFailedThumbIdx] = useState<Set<number>>(new Set());
  const [photoPanelStyle, setPhotoPanelStyle] = useState<React.CSSProperties>({});

  // 加载任务详情
  useEffect(() => {
    if (!taskId) return;
    const loadTask = async () => {
      setLoading(true);
      try {
        const res = await fetch(`${GATEWAY_URL}/api/history/task/${encodeURIComponent(taskId)}`);
        const data = await res.json();
        if (data.code === 200 && data.data) {
          setTaskDetails(data.data.details || []);
          const rawTaskId = data.data.taskId || "";
          const rawDate = rawTaskId.length >= 10 ? rawTaskId.substring(2, 10) : "";
          setTaskMeta({
            operator: data.data.operator || "",
            hasModified: data.data.hasModified || false,
            modifiedBins: data.data.modifiedBins || [],
            taskDate: rawDate,
            isValid: data.data.isValid !== undefined ? data.data.isValid : true,
          });
          // 默认选中第一个
          if (data.data.details?.length > 0) {
            setSelectedBin(data.data.details[0]);
          }
        } else {
          toast.error("加载任务详情失败");
        }
      } catch (e) {
        toast.error("加载任务详情失败: " + (e as Error).message);
      } finally {
        setLoading(false);
      }
    };
    loadTask();
  }, [taskId]);

  // 统计
  const totalBins = taskDetails.length;
  const matchedBins = taskDetails.filter(d => d.差异 === "一致").length;
  const diffBins = totalBins - matchedBins;

  // 构建图片URL
  const buildImageUrls = (detail: InventoryDetail): string[] => {
    const paths = [detail.照片1路径, detail.照片2路径, detail.照片3路径, detail.照片4路径];
    return paths.map(path => {
      if (!path || path.trim() === "") return "";
      const normalizedPath = path.startsWith("/") ? path.substring(1) : path;
      const parts = normalizedPath.split("/");
      if (parts.length < 4) return "";
      const cameraType = parts[2].toLowerCase();
      const filename = parts[3].split(".")[0];
      return `${GATEWAY_URL}/api/history/image?taskNo=${parts[0]}&binLocation=${parts[1]}&cameraType=${cameraType}&filename=${filename}&source=capture_img`;
    }).filter(Boolean);
  };

  // photoUrls 变化时也要重置图片错误状态，防止切换库位后残留
  useEffect(() => {
    setMainImgError(false);
    setFailedThumbIdx(new Set());
  }, [photoUrls]);

  // 当选中的库位变化时，重新构建照片URL
  useEffect(() => {
    if (selectedBin) {
      const urls = buildImageUrls(selectedBin);
      setPhotoUrls(urls);
      setSelectedPhotoIdx(0);
      setMainImgError(false);
    } else {
      setPhotoUrls([]);
      setSelectedPhotoIdx(0);
      setMainImgError(false);
    }
  }, [selectedBin]);

  // 计算照片面板位置，使其始终垂直居中于当前视口
  useEffect(() => {
    const HEADER_HEIGHT = 64; // header 高度约 64px
    const PANEL_HEIGHT = 480; // 照片面板预估高度
    const PANEL_WIDTH = 384;  // w-96 = 24rem = 384px

    const updatePosition = () => {
      const viewportH = window.innerHeight;
      const availableH = viewportH - HEADER_HEIGHT;
      // 面板上下各留 16px 边距
      const maxH = availableH - 32;
      const top = HEADER_HEIGHT + Math.max(16, (availableH - PANEL_HEIGHT) / 2);
      setPhotoPanelStyle({
        position: "fixed",
        right: 16,
        top: Math.min(top, viewportH - PANEL_HEIGHT - 16),
        width: PANEL_WIDTH,
        maxHeight: maxH,
      });
    };

    updatePosition();
    window.addEventListener("scroll", updatePosition, { passive: true });
    window.addEventListener("resize", updatePosition);
    return () => {
      window.removeEventListener("scroll", updatePosition);
      window.removeEventListener("resize", updatePosition);
    };
  }, []);

  const formatDate = (dateStr: string) => {
    if (!dateStr) return "";
    // 兼容 YYYYMMDD 和 YYYY-MM-DD 两种格式
    try {
      const normalized = dateStr.replace(/-/g, "");
      if (normalized.length === 8) {
        return `${normalized.substring(0, 4)}年${parseInt(normalized.substring(4, 6))}月${parseInt(normalized.substring(6, 8))}日`;
      }
      const d = new Date(dateStr);
      return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`;
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="min-h-screen flex flex-col bg-gray-50">
      {/* 背景 */}
      <div
        className="absolute inset-0 bg-cover bg-center opacity-5"
        style={{
          backgroundImage: "url(https://lf-code-agent.coze.cn/obj/x-ai-cn/attachment/3868529628819536/背景参考_20250808011802.jfif)",
        }}
      ></div>

      {/* 顶部导航栏 */}
      <header className="relative bg-white shadow-md z-10">
        <div className="container mx-auto px-4 py-3 flex justify-between items-center">
          <div className="flex items-center space-x-2">
            <div className="w-10 h-10 bg-green-700 rounded-full flex items-center justify-center">
              <i className="fa-solid fa-boxes-stacked text-white text-xl"></i>
            </div>
            <div>
              <h1 className="text-xl font-bold text-green-800">中国烟草</h1>
              <p className="text-xs text-gray-500">智慧仓库盘点系统</p>
            </div>
          </div>
          <div className="flex items-center space-x-3">
            <div className="text-right hidden md:block">
              <p className="text-sm font-medium text-gray-700">欢迎，{userName || "用户"}</p>
              <p className="text-xs text-gray-500">权限：{userLevel === "admin" ? "管理员" : "操作员"}</p>
            </div>
            <div className={`w-10 h-10 rounded-full flex items-center justify-center ${userLevel === "admin" ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"}`}>
              <i className={`fa-solid ${userLevel === "admin" ? "fa-user-shield" : "fa-user"}`}></i>
            </div>
            <button
              onClick={() => navigate("/inventory/history")}
              className="bg-gray-600 hover:bg-gray-700 text-white px-4 py-2 rounded-lg transition-all flex items-center"
            >
              <i className="fa-solid fa-arrow-left mr-2"></i>返回
            </button>
          </div>
        </div>
      </header>

      {/* 主内容 */}
      <main className="flex-1 container mx-auto px-4 py-8 relative z-10">
        {loading ? (
          <div className="flex items-center justify-center py-20">
            <i className="fa-solid fa-spinner fa-spin text-4xl text-green-600 mr-3"></i>
            <span className="text-gray-600">加载中...</span>
          </div>
        ) : (
          <div className="space-y-6">
            {/* 任务信息卡片 */}
            <div className="bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
              <div className="flex flex-col md:flex-row">
                {/* 左侧：任务基本信息 */}
                <div className="flex-1 px-6 py-5 border-b md:border-b-0 md:border-r border-gray-200">
                  <h2 className="text-3xl font-bold text-green-800 mb-2">{taskId}</h2>
                  <div className="flex flex-col gap-y-1 text-lg text-gray-600">
                    <span><i className="fa-solid fa-calendar mr-2 w-5"></i>{formatDate(taskMeta.taskDate)}</span>
                    <span><i className="fa-solid fa-user mr-2 w-5"></i>{taskMeta.operator || "-"}</span>
                    {taskMeta.hasModified ? (
                      <span className="font-bold text-yellow-700">
                        <i className="fa-solid fa-pen mr-2 w-5"></i>存在人工修改
                      </span>
                    ) : (
                      <span className="text-green-600">
                        <i className="fa-solid fa-circle-check mr-2 w-5"></i>无人工修改
                      </span>
                    )}
                  </div>
                </div>
                {/* 右侧：统计数字 */}
                <div className="flex items-center gap-0">
                  {/* 盘点状态标志 */}
                  <div className="px-5 py-4 text-center border-r border-gray-200">
                    {!taskMeta.isValid ? (
                      <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-red-200 text-red-900 border-2 border-red-400 whitespace-nowrap">
                        <i className="fa-solid fa-xmark mr-1"></i>无效盘点
                      </span>
                    ) : taskMeta.hasModified ? (
                      <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-yellow-200 text-yellow-900 border-2 border-yellow-400 whitespace-nowrap">
                        <i className="fa-solid fa-pen mr-1"></i>有效修正盘点
                      </span>
                    ) : (
                      <span className="inline-flex items-center px-4 py-2 rounded-full text-sm font-bold bg-green-200 text-green-900 border-2 border-green-400 whitespace-nowrap">
                        <i className="fa-solid fa-check mr-1"></i>有效盘点
                      </span>
                    )}
                  </div>
                  {/* 统计区 */}
                  <div className="flex divide-x divide-gray-200">
                    <div className="px-5 py-4 text-center min-w-[80px]">
                      <p className="text-4xl font-bold text-gray-800">{totalBins}</p>
                      <p className="text-sm text-gray-500 mt-0.5">下发库位</p>
                    </div>
                    <div className="px-5 py-4 text-center min-w-[80px] bg-green-50">
                      <p className="text-4xl font-bold text-green-600">{matchedBins}</p>
                      <p className="text-sm text-green-600 mt-0.5">一致库位</p>
                    </div>
                    <div className="px-5 py-4 text-center min-w-[80px]">
                      <p className={`text-4xl font-bold ${totalBins > 0 ? (diffBins > 0 ? "text-red-500" : "text-gray-400") : "text-gray-400"}`}>
                        {totalBins > 0 ? `${Math.round(diffBins / totalBins * 100)}%` : "0%"}
                      </p>
                      <p className="text-sm text-gray-500 mt-0.5">异常比例</p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* 表格 + 照片区域 */}
            <div className="flex gap-6">
              {/* 左侧：详情表格 */}
              <div className="flex-1 bg-white rounded-xl shadow-md overflow-hidden border border-gray-100">
                <div className="px-6 py-4 border-b border-gray-200 bg-gray-50">
                  <h3 className="text-lg font-semibold text-gray-800">
                    <i className="fa-solid fa-list mr-2"></i>
                    盘点明细
                  </h3>
                </div>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead className="bg-gray-100 text-gray-600">
                      <tr>
                        <th className="px-5 py-4 text-left font-medium">库位号</th>
                        <th className="px-5 py-4 text-left font-medium">系统品规</th>
                        <th className="px-5 py-4 text-left font-medium">盘点品规</th>
                        <th className="px-5 py-4 text-center font-medium">系统数量</th>
                        <th className="px-5 py-4 text-center font-medium">盘点数量</th>
                        <th className="px-5 py-4 text-center font-medium">是否一致</th>
                        <th className="px-5 py-4 text-center font-medium">修改类型</th>
                      </tr>
                    </thead>
                    <tbody>
                      {taskDetails.map((detail, idx) => {
                        const isConsistent = detail.差异 === "一致";
                        const isManualModified = detail.修改记录 === "人工修改";
                        return (
                          <tr
                            key={idx}
                            className={`border-b border-gray-100 hover:bg-gray-50 ${
                              selectedBin?.储位名称 === detail.储位名称 ? "bg-blue-50" : ""
                            }`}
                            onClick={() => setSelectedBin(detail)}
                            style={{ cursor: "pointer" }}
                          >
                            <td className="px-5 py-4 font-medium text-gray-800">
                              {detail.储位名称}
                            </td>
                            <td className="px-5 py-4 text-gray-600">
                              {detail.品规名称}
                            </td>
                            <td className="px-5 py-4 text-gray-600">
                              <span className={detail.实际品规 !== detail.品规名称 ? "text-red-600 font-medium" : ""}>
                                {detail.实际品规 || "-"}
                              </span>
                            </td>
                            <td className="px-5 py-4 text-center text-blue-600 font-medium">
                              {detail.库存数量}
                            </td>
                            <td className="px-5 py-4 text-center font-medium">
                              <span className={detail.差异 !== "一致" ? "text-red-600" : "text-gray-800"}>
                                {detail.实际数量}
                              </span>
                            </td>
                            <td className="px-5 py-4 text-center">
                              {isConsistent ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-green-200 text-green-900 border border-green-400">
                                  <i className="fa-solid fa-check mr-1"></i>一致
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-red-200 text-red-900 border border-red-400">
                                  <i className="fa-solid fa-xmark mr-1"></i>不一致
                                </span>
                              )}
                            </td>
                            <td className="px-5 py-4 text-center">
                              {isManualModified ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-yellow-200 text-yellow-900 border border-yellow-400">
                                  <i className="fa-solid fa-pen mr-1"></i>人工修改
                                </span>
                              ) : isConsistent ? (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-gray-100 text-gray-600 border border-gray-300">
                                  <i className="fa-solid fa-minus mr-1"></i>无修改
                                </span>
                              ) : (
                                <span className="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-bold bg-orange-200 text-orange-900 border border-orange-400">
                                  <i className="fa-solid fa-robot mr-1"></i>系统修改
                                </span>
                              )}
                            </td>
                          </tr>
                        );
                      })}
                    </tbody>
                  </table>
                </div>
              </div>
            </div>

            {/* 右侧浮动照片展示区域 */}
            <div
              style={photoPanelStyle}
              className="bg-white rounded-xl shadow-lg overflow-hidden border border-gray-200 flex flex-col z-50"
            >
              <div className="px-6 py-4 border-b border-gray-200 bg-gray-50 flex-shrink-0">
                <h3 className="text-lg font-semibold text-gray-800">
                  <i className="fa-solid fa-image mr-2"></i>
                  照片展示
                </h3>
              </div>
              <div className="flex-1 p-4 flex flex-col overflow-y-auto">
                {selectedBin ? (
                  <div className="flex flex-col">
                    {/* 选中库位标题 */}
                    <div className="mb-3 text-center">
                      <p className="text-base font-bold text-gray-800">{selectedBin.储位名称}</p>
                      <p className="text-sm text-gray-500">{selectedBin.品规名称} → {selectedBin.实际品规}</p>
                      <p className="text-sm text-gray-500">
                        系统数量: <span className="text-blue-600 font-medium">{selectedBin.库存数量}</span> |
                        盘点数量: <span className={`font-medium ${selectedBin.差异 !== "一致" ? "text-red-600" : "text-gray-800"}`}>{selectedBin.实际数量}</span>
                      </p>
                    </div>

                    {/* 大图 */}
                    <div className="flex items-center justify-center bg-gray-100 rounded-lg overflow-hidden relative min-h-[200px]">
                      {photoUrls.length > 0 ? (
                        <img
                          src={photoUrls[selectedPhotoIdx]}
                          alt={`照片 ${selectedPhotoIdx + 1}`}
                          className="max-h-48 max-w-full object-contain cursor-pointer"
                          onClick={() => {
                            window.open(photoUrls[selectedPhotoIdx], "_blank");
                          }}
                          onError={() => setMainImgError(true)}
                        />
                      ) : mainImgError ? (
                        <div className="text-center text-gray-400 py-4">
                          <i className="fa-solid fa-image text-4xl mb-2 block"></i>
                          <p className="text-sm">图片加载失败</p>
                        </div>
                      ) : (
                        <div className="text-center text-gray-400 py-4">
                          <i className="fa-solid fa-image text-4xl mb-2 block"></i>
                          <p className="text-sm">暂无照片</p>
                        </div>
                      )}
                    </div>

                    {/* 照片说明 */}
                    <div className="grid grid-cols-4 gap-1 text-xs text-gray-500 text-center mt-2">
                      <span>3D主图</span>
                      <span>3D深度图</span>
                      <span>扫描相机1</span>
                      <span>扫描相机2</span>
                    </div>

                    {/* 缩略图 */}
                    {photoUrls.length > 1 && (
                      <div className="flex justify-center gap-2 mt-2">
                        {photoUrls.map((url, idx) => {
                          if (failedThumbIdx.has(idx)) return null;
                          return (
                            <img
                              key={idx}
                              src={url}
                              alt={`照片 ${idx + 1}`}
                              onClick={() => setSelectedPhotoIdx(idx)}
                              className={`w-16 h-16 object-cover rounded cursor-pointer border-2 transition-all ${
                                selectedPhotoIdx === idx ? "border-blue-500 opacity-100" : "border-gray-200 opacity-60 hover:opacity-100"
                              }`}
                              onError={() => setFailedThumbIdx(prev => new Set([...prev, idx]))}
                            />
                          );
                        })}
                      </div>
                    )}
                  </div>
                ) : (
                  <div className="flex flex-col items-center justify-center text-gray-400 flex-1">
                    <i className="fa-solid fa-hand-point-up text-5xl mb-4"></i>
                    <p className="text-base font-medium">点击左侧表格中的库位</p>
                    <p className="text-sm mt-1">查看对应照片</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
