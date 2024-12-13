import { app } from "/scripts/app.js";
import { $el } from "/scripts/ui.js";
import { api } from '/scripts/api.js';

app.registerExtension({
    name: "LivePhoto.Preview",
    async beforeRegisterNodeDef(nodeType, nodeData) {
        if (nodeData.name !== "LivePhotoPreview") {
            return;
        }

        console.log("[LivePhoto] Setting up LivePhotoPreview node");

        nodeType.prototype.onNodeCreated = function() {
            console.log("[LivePhoto] Node created");

            // 创建预览widget
            const widget = {
                type: "div",
                name: "preview",
                draw(ctx, node, widget_width, y, widget_height) {
                    const margin = 10;
                    const buttonHeight = 40; // 为按钮预留空间
                    const elRect = ctx.canvas.getBoundingClientRect();
                    const transform = new DOMMatrix()
                        .scaleSelf(
                            elRect.width / ctx.canvas.width,
                            elRect.height / ctx.canvas.height
                        )
                        .multiplySelf(ctx.getTransform())
                        .translateSelf(margin, margin + y + buttonHeight); // 添加buttonHeight偏移

                    Object.assign(this.div.style, {
                        transformOrigin: "0 0",
                        transform: transform,
                        position: "absolute",
                        left: document.querySelector('.comfy-menu').style.display === 'none' ? '60px' : '0',
                        top: "0",
                        width: `${widget_width - margin * 2}px`,
                        height: "200px", // 减小高度，给按钮留空间
                        zIndex: 1
                    });
                },
                computeSize(width) {
                    return [width, width * 1.2];
                }
            };

            // 创建预览容器
            widget.div = $el("div", {
                className: "livephoto-preview",
                style: {
                    width: "100%",
                    height: "100%",
                    border: "2px solid #333",
                    borderRadius: "4px",
                    backgroundColor: "#1a1a1a",
                    overflow: "hidden",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center"
                }
            });

            // 创建视频元素
            widget.videoEl = $el("video", {
                style: {
                    width: "100%",
                    height: "100%",
                    objectFit: "contain"
                },
                controls: true,
                muted: true,
                loop: true,
                playsInline: true
            });

            // 添加事件监听
            widget.videoEl.addEventListener("loadedmetadata", () => {
                console.log("[LivePhoto] Video loaded:", widget.videoEl.videoWidth, "x", widget.videoEl.videoHeight);
                this.setSize([this.size[0], this.computeSize([this.size[0], this.size[1]])[1]]);
                if (this.graph) {
                    this.graph.setDirtyCanvas(true);
                }
            });

            widget.videoEl.addEventListener("error", (e) => {
                console.error("[LivePhoto] Video load error:", e);
                widget.div.innerHTML = `
                    <div style="color: red; text-align: center; padding: 10px;">
                        Error loading video: ${e.message}
                    </div>
                `;
            });

            // 添加到DOM
            widget.div.appendChild(widget.videoEl);
            document.body.appendChild(widget.div);
            this.addCustomWidget(widget);

            // 设置节点大小
            this.setSize([220, 320]);

            // 添加尺寸计算
            this.computeSize = function(size) {
                size = size || this.size;
                return [size[0], 320]; // 固定高度
            };

            // 清理函数
            const onRemoved = this.onRemoved;
            this.onRemoved = () => {
                widget.div.remove();
                return onRemoved?.();
            };

            // 修改 onExecuted
            this.onExecuted = function(message) {
                console.log("[LivePhoto] Node executed with message:", message);

                if (!message?.video) {
                    console.warn("[LivePhoto] No video data in message");
                    return;
                }

                try {
                    let videoPath = message.video;
                    
                    // 如果是数组，将其合并为字符串
                    if (Array.isArray(videoPath)) {
                        videoPath = videoPath.join('');
                    }
                    
                    console.log("[LivePhoto] Creating preview for video:", videoPath);

                    // 获取文件名
                    const filename = videoPath.split('/').pop();
                    const folderName = videoPath.split('/').slice(-2, -1)[0];
                    
                    // 设置视频源
                    const params = new URLSearchParams();
                    params.append("subfolder", folderName);
                    params.append("type", "output");
                    params.append("filename", filename);
                    const videoUrl = api.apiURL(`/view?${params.toString()}`);
                    
                    console.log("[LivePhoto] Video URL:", videoUrl);
                    console.log("[LivePhoto] Full path:", videoPath);
                    console.log("[LivePhoto] Folder:", folderName);
                    console.log("[LivePhoto] Filename:", filename);
                    
                    // 清除旧的错误信息并重新添加视频元素
                    widget.div.innerHTML = '';
                    widget.div.appendChild(widget.videoEl);
                    widget.videoEl.src = videoUrl;

                } catch (error) {
                    console.error("[LivePhoto] Error creating preview:", error);
                    widget.div.innerHTML = `
                        <div style="color: red; text-align: center; padding: 10px;">
                            Error: ${error.message}
                        </div>
                    `;
                }
            };
        };
    }
});

console.log("[LivePhoto] Extension loaded");
