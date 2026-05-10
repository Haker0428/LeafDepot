import { motion } from "framer-motion";

interface PhotoGroup {
  top?: string;
  bottom?: string;
}

interface Props {
  photoGroups: PhotoGroup[];
  currentGroupIndex: number;
  setCurrentGroupIndex: (index: number) => void;
  imageLoading: boolean;
  imageError: boolean;
  handleImageLoad: () => void;
  handleImageError: () => void;
  setLightboxImage: (url: string | null) => void;
}

export default function PhotoGallery({
  photoGroups,
  currentGroupIndex,
  setCurrentGroupIndex,
  imageLoading,
  handleImageLoad,
  handleImageError,
  setLightboxImage,
}: Props) {
  const currentGroup = photoGroups[currentGroupIndex];
  const topPhoto = currentGroup?.top;
  const bottomPhoto = currentGroup?.bottom;
  const is3DCamera = currentGroupIndex === 0;

  return (
    <motion.div
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.5, delay: 0.2 }}
      className="lg:col-span-1"
    >
      <div className="bg-white rounded-xl shadow-md border border-gray-100 h-full flex flex-col">
        <div className="p-6 border-b border-gray-100">
          <h3 className="text-xl font-bold text-green-800 flex items-center">
            <i className="fa-solid fa-eye mr-2 text-green-600"></i>
            观察窗口
          </h3>
        </div>

        <div className="flex-1 p-4 flex flex-col gap-4">
          {/* 上半部分 */}
          <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
            <div className="relative w-full h-full max-w-md mx-auto">
              {imageLoading ? (
                <div className="absolute inset-0 flex items-center justify-center">
                  <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-green-700"></div>
                </div>
              ) : topPhoto ? (
                <>
                  <img
                    src={topPhoto}
                    alt={is3DCamera ? "3D相机-主图" : "扫码相机-扫码图1"}
                    className="max-w-full max-h-full object-contain rounded-lg border-2 border-green-700 cursor-zoom-in"
                    onLoad={handleImageLoad}
                    onError={handleImageError}
                    onClick={() => setLightboxImage(topPhoto)}
                  />
                  <div className="absolute top-2 left-2 bg-green-700 text-white text-xs font-bold px-2 py-1 rounded-full">
                    {is3DCamera ? "主图" : "扫码图1"}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center p-4">
                  <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                    <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                  </div>
                  <p className="text-gray-500 text-sm">画面未连接</p>
                </div>
              )}
            </div>
          </div>

          {/* 下半部分 */}
          <div className="bg-gray-100 rounded-lg border border-gray-300 overflow-hidden flex-1 flex items-center justify-center">
            <div className="relative w-full h-full max-w-md mx-auto">
              {bottomPhoto ? (
                <>
                  <img
                    src={bottomPhoto}
                    alt={is3DCamera ? "3D相机-深度图" : "扫码相机-扫码图2"}
                    className="max-w-full max-h-full object-contain rounded-lg border-2 border-green-700 cursor-zoom-in"
                    onLoad={handleImageLoad}
                    onError={handleImageError}
                    onClick={() => setLightboxImage(bottomPhoto)}
                  />
                  <div className="absolute top-2 left-2 bg-blue-700 text-white text-xs font-bold px-2 py-1 rounded-full">
                    {is3DCamera ? "深度图" : "扫码图2"}
                  </div>
                </>
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-center p-4">
                  <div className="w-16 h-16 bg-gray-200 rounded-full flex items-center justify-center mb-2">
                    <i className="fa-solid fa-camera text-gray-500 text-2xl"></i>
                  </div>
                  <p className="text-gray-500 text-sm">等待照片加载...</p>
                </div>
              )}
            </div>
          </div>

          {/* 照片组切换按钮 */}
          <div className="flex justify-center gap-2">
            {[
              { index: 0, label: "3D相机", subLabel: "主图/深度图" },
              { index: 1, label: "扫码相机", subLabel: "扫码图1/图2" },
            ].map(({ index, label, subLabel }) => {
              const group = photoGroups[index];
              const hasPhoto = group.top || group.bottom;
              return (
                <button
                  key={index}
                  onClick={() => setCurrentGroupIndex(index)}
                  disabled={!hasPhoto}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    currentGroupIndex === index
                      ? "bg-green-700 text-white"
                      : hasPhoto
                        ? "bg-gray-200 text-gray-700 hover:bg-gray-300"
                        : "bg-gray-100 text-gray-400 cursor-not-allowed"
                  }`}
                >
                  <span>{label}</span>
                  {hasPhoto && (
                    <span className="block text-xs opacity-75 font-normal">
                      {subLabel}
                    </span>
                  )}
                </button>
              );
            })}
          </div>
        </div>
      </div>
    </motion.div>
  );
}
