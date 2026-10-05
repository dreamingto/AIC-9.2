# 比赛材料源文件

匿名技术报告、8 页答辩幻灯片、项目简介和中文逐字稿在本目录维护。实际 PDF、截图、原始排名和 MP4 生成到 `output/competition/`，通过独立发布包提供，不把生成物和真实原图混入源码。

`vendor/` 来自 HTML PPT Studio 的 presenter-mode-reveal 模板、academic-paper 主题与运行时，保留 MIT LICENSE。没有外部字体或 CDN；箭头翻页，S 演讲者模式，F 全屏，O 总览。

在独立材料环境安装 Python 的 reportlab、pypdf、Pillow、imageio-ffmpeg（实际制作环境锁见 requirements.lock），避免修改 OCR / 检索环境。Windows 中文报告字体使用系统 SimSun，语音使用本机 Huihui SAPI；未安装这些资源时明确报错。

先运行后端 `scripts.prepare_competition_assets` 从冻结扫描裁出素材，再完成 `scripts.run_domestic_comparison`，将其最新 `comparison.json` 传给：

```powershell
python competition/build_materials.py --report <comparison.json绝对路径>
$env:E2E_BASE_URL='http://127.0.0.1:8088'
node competition/capture.mjs
powershell -File competition/narrate.ps1
python competition/mux_video.py prepare
node competition/capture.mjs --video
python competition/mux_video.py mux --recording <录制webm绝对路径>
```

捕获使用前端锁定的 Playwright 与本机 Chrome。视频是实际浏览器录制：两段案例发送真实 API 请求并进入候选页，其他画面为答辩页；中文语音本机生成。没有合成 API 响应、预设排名或提交真实古籍核验。运行时长来自实际 WAV 探测，超出 3–5 分钟会拒绝制作。报告与演示如实写明开发集、AI 草稿和 `not_evaluated` 指标。

正式比赛网站上传仍由参赛者操作；本工具不填写队员、学校、导师或报名信息。
