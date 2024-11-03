import { app } from "../../../scripts/app.js";
import { api } from '../../../scripts/api.js';

console.log("[LivePhoto] Loading extension...");

function createVideoPreview(node, videoPath) {
    console.log("[LivePhoto] Creating preview for video:", videoPath);
    
    // 如果视频路径是数组，将其合并
    if (Array.isArray(videoPath)) {
        videoPath = videoPath.join('');
    }

    // 从完整路径中提取相对路径
    // 例如从 '/home/chi/ComfyUI/output/livephoto_xxx/IMG.MOV' 
    // 提取 'livephoto_xxx/IMG.MOV'
    const pathParts = videoPath.split('/');
    const outputIndex = pathParts.indexOf('output');
    const relativePath = pathParts.slice(outputIndex + 1).join('/');
    
    console.log("[LivePhoto] Using relative path:", relativePath);

    // 创建预览元素
    const element = document.createElement("div");
    element.style.width = "100%";
    element.style.height = "auto";
    element.style.backgroundColor = "#1a1a1a";
    element.style.borderRadius = "8px";
    element.style.overflow = "hidden";
    element.style.marginTop = "10px";

    // 创建视频容器
    const container = document.createElement("div");
    container.style.width = "100%";
    container.style.position = "relative";
    container.style.paddingBottom = "56.25%"; // 16:9 aspect ratio

    // 创建视频元素
    const video = document.createElement("video");
    video.style.position = "absolute";
    video.style.top = "0";
    video.style.left = "0";
    video.style.width = "100%";
    video.style.height = "100%";
    video.style.objectFit = "contain";
    video.controls = true;
    video.muted = true;
    video.loop = true;

    // 设置视频源
    const params = new URLSearchParams();
    params.append("filename", relativePath);
    const videoUrl = api.apiURL(`/view?${params.toString()}`);
    console.log("[LivePhoto] Video URL:", videoUrl);
    video.src = videoUrl;
    
    // 添加到 DOM
    container.appendChild(video);
    element.appendChild(container);

    // 添加事件监听
    video.addEventListener("loadedmetadata", () => {
        console.log("[LivePhoto] Video loaded:", video.videoWidth, "x", video.videoHeight);
        // 更新大小
        node.setSize([node.size[0], node.computeSize([node.size[0], node.size[1]])[1]]);
        if (node.graph) {
            node.graph.setDirtyCanvas(true);
        }
    });

    video.addEventListener("error", (e) => {
        console.error("[LivePhoto] Video load error:", e);
        if (video.error) {
            console.error("[LivePhoto] Video error details:", {
                code: video.error.code,
                message: video.error.message
            });
        }
    });

    return element;
}

app.registerExtension({
    name: "LivePhoto.Preview",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LivePhotoPreview") {
            return;
        }

        console.log("[LivePhoto] Setting up LivePhotoPreview node");

        // 修改 onNodeCreated
        const onNodeCreated = nodeType.prototype.onNodeCreated;
        nodeType.prototype.onNodeCreated = function() {
            if (onNodeCreated) {
                onNodeCreated.apply(this, arguments);
            }

            // 添加预览 widget
            this.addWidget(
                "preview",
                "preview",
                "",
                () => {},
                {
                    getValue: () => "",
                    setValue: () => {}
                }
            );

            console.log("[LivePhoto] Node created");
        };

        // 修改 onExecuted
        const onExecuted = nodeType.prototype.onExecuted;
        nodeType.prototype.onExecuted = function(message) {
            console.log("[LivePhoto] Node executed with message:", message);

            if (!message?.video) {
                console.warn("[LivePhoto] No video data in message");
                return;
            }

            try {
                // 找到预览 widget
                const widget = this.widgets.find(w => w.name === "preview");
                if (!widget) {
                    console.error("[LivePhoto] Preview widget not found");
                    return;
                }

                // 创建新的预览
                const previewElement = createVideoPreview(this, message.video);
                widget.element = previewElement;

            } catch (error) {
                console.error("[LivePhoto] Error creating preview:", error);
                console.error(error.stack);
            }

            if (onExecuted) {
                onExecuted.apply(this, arguments);
            }
        };

        // 添加尺寸计算
        nodeType.prototype.computeSize = function(size) {
            size = size || this.size;
            return [size[0], size[0] * (9/16) + 40]; // 16:9 aspect ratio + padding
        };

        console.log("[LivePhoto] Node setup complete");
    }
});

console.log("[LivePhoto] Extension loaded");
