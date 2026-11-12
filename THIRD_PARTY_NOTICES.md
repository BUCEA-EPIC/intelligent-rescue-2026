# Third-Party Notices

本仓库包含或依赖以下第三方项目与资源。根目录的 [MIT License](LICENSE) 仅适用于项目作者拥有版权的原创代码，不改变第三方代码、依赖及非源码资源的许可要求。

## 继承代码

- 来源：[Intelligent Rescue 2025](https://github.com/miofelix/intelligent-rescue-2025)。
- 原作者：樊彧、覃启轩，来自北京建筑大学工程实践创新中心 314 工作室。
- 许可：MIT License，版权声明保留在根目录 [LICENSE](LICENSE) 中。

## Ultralytics YOLO

- 项目：[ultralytics/ultralytics](https://github.com/ultralytics/ultralytics)。
- 用途：Jetson 上位机的 YOLO 目标检测与推理。
- 使用位置：[jetson/main.py](jetson/main.py) 与 [jetson/vision.py](jetson/vision.py)。
- 许可：开源版本采用 AGPL-3.0，另提供 Enterprise 商业授权，详见 [官方许可说明](https://www.ultralytics.com/license)。

Ultralytics 代码的许可不因本项目原创代码采用 MIT License 而改变。

## 波特律动 / Keysking OLED 驱动与字库

- 用途：STM32 侧 SSD1306 OLED 显示、ASCII / 中文字库与图模数据。
- 使用位置：[oled.c](stm32/hardware/oled.c)、[oled.h](stm32/hardware/oled.h)、[font.c](stm32/hardware/font.c)、[font.h](stm32/hardware/font.h)。
- 已知来源：`oled.c` 文件头注明“波特律动 / Keysking”，配套资源注明使用波特律动 LED 取模工具生成字模与图模。
- 已知许可：`oled.c` 文件头声明 MIT License，现有来源与许可注释均予保留。

配套字体与图模文件未单独附带完整许可证，其授权范围以原始来源及权利人的声明为准。

## 其他运行时依赖

Jetson 程序还依赖 PyTorch、OpenCV、NumPy 和 pyserial；STM32 核心模块依赖 STM32 HAL。上述依赖分别适用各自许可证，具体条款以所使用版本的上游声明为准。

## 电路板生产资料

`electronics/` 中的 Gerber、BOM 与贴片坐标属于硬件生产资料，不自动适用本项目源码的 MIT License。

## 图片和媒体素材

`images/` 中的获奖证书与比赛照片不采用 MIT License。除非另有明确许可，相关权利均予保留。
