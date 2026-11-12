#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 文件：config.py
# 功能：全局参数与资源路径配置
# 团队：北京建筑大学光启Ray-space工作室

"""
配置中心

本模块提供全局配置参数，同时保持与现有接口的兼容性。外部模块可通过以下属性访问配置：

属性：
    team (str): 当前选择的队伍，必须是 'blue' 或 'red'
    rescue_model (str): 模型权重文件路径
    label_balls (list): 根据当前队伍过滤后的球体标签列表
    label_area (list): 根据当前队伍过滤后的区域标签列表
"""

from pathlib import Path
from typing import Tuple

_JETSON_DIR = Path(__file__).resolve().parent

# 用户可配置参数
# 队伍配置
TEAM: str = ["blue", "red"][0]  # 当前队伍（默认选第一个）
RESCUE_MODEL = str(_JETSON_DIR / "models" / "rescue.pt")  # 本地模型文件路径

# 视频输出配置
VIDEO_OUTPUT_DIR = str(_JETSON_DIR / "outputs" / "videos")  # 视频保存目录
SAVE_OUTPUT: bool = False  # 默认启用视频保存
VIDEO_CODEC: str = "mp4v"  # 视频编码格式
DEFAULT_FPS: int = 30  # 默认帧率
DEFAULT_RESOLUTION: Tuple[int, int] = (640, 480)  # 默认分辨率

# 区域坐标设置：(x1, y1, x2, y2)
# 抓取区域 - 爪子能够成功抓取球体的区域 (X轴稍微缩小一点，要求对得更准)
CATCH_AREA: Tuple[int, int, int, int] = (210, 370, 430, 490)

# 准备区域 - 开始执行靠近球体的区域
READY_AREA: Tuple[int, int, int, int] = (160, 178, 480, 388)

# 持球区域 - 成功抓取后球体应处的位置 (Y轴范围稍微加大一点点，向上放宽至350)
HOLDING_AREA: Tuple[int, int, int, int] = (200, 350, 440, 480)

# 冲刺区域
CENTER_REGION: Tuple[int, int, int, int] = (250, 208, 390, 348)

CROSS_CENTER_REGION = (170, 430, 480, 460)

# 舵机角度设置：舵机 1 和舵机 2 的角度
CATCH_ANGLE: Tuple[int, int] = (82,82)
RELEASE_ANGLE: Tuple[int, int] = (0,0)

# 串口设备口
UART_PORT: str = "/dev/ttyUSB0"
# UART_PORT: str = "COM9"

# 运动与 PWM 参数配置
# 注意：因为下位机已经改为纯开环直传PWM，下方的速度参数实际上代表PWM占空比。
# 原本的代码中数值较小（如230、800），目前保留了原数字。烧录后请根据实际电机的启动PWM调大这些数值。

# 下位机速度系数（所有传输到下位机的速度数据均会乘以该系数）
SPPPEELEMENT: float = 0.32

# 1. 基础硬件限制
PWM_MIN_LIMIT: int = 500  # 最小物理限制（实际输出的电机起步死区 PWM 占空比，小于此值强行拉高）

# 2. 状态0与状态2：寻找目标与卡死脱困
SPEED_SEARCH_BALL: int = 2300  # 没找到球时的原地自转寻找速度（原2050 * 31/30）
SPEED_SEARCH_AREA: int = 1800  # 没找到安全区时的原地自转寻找速度（原1800 * 31/30）
SPEED_STUCK_BACKWARD: int = 2728  # 发现底盘卡死时的倒车后撤速度（原2640 * 31/30）
SPEED_STUCK_TURN: int = 2108  # 发现底盘卡死时的倒车后甩头脱困速度（原2040 * 31/30）
SPEED_STUCK_AREA_BACKWARD: int = 2480  # 找区域卡死时的后撤速度（原2400 * 31/30）
SPEED_STUCK_AREA_TURN: int = 2480  # 找区域卡死时的甩头速度（原2400 * 31/30）
SPEED_BLIND_DASH: int = 2108  # 找区域超时(2.5圈)后的盲目前冲速度（原2040 * 31/30）

# 3. 状态1：抛弃错误球体动作
SPEED_DISCARD_TURN: int = 2560  # 抓到错误颜色球时，甩头拨开球的速度（原1800 * 31/30）
SPEED_DISCARD_BACKWARD: int = 2480  # 拨开球后的倒退速度（原2400 * 31/30）

# 4. 状态3：放球与后撤系列动作
SPEED_STATE3_DASH: int = 2000  # 到达安全区后的最后前冲速度（原2200 * 31/30）
SPEED_STATE3_BACKWARD: int = 2232  # 放球后的后撤离开速度（原2160 * 31/30）
SPEED_STATE3_TURN: int = 3300  # 放球后的甩头寻找下个目标速度（原2160 * 31/30）
RELEASE_FORWARD_TIME: float = 1.7  # 放球前冲的时间 (秒)
RELEASE_BACKWARD_TIME: float = 1.5  # 放球后后退的时间 (秒)
RELEASE_TURN_TIME: float = 1.0  # 后退完毕后，转身180°的时间 (秒)

# 5. 追踪球体 (approach_ball) 参数
# PID 控制器参数
TRACK_BALL_KP: float = 0.04  # （原代码值为 0.003，放大10倍以适配PWM）
TRACK_BALL_KI: float = 0.000  # （原代码值为 0.000）
TRACK_BALL_KD: float = 0.1  # （原代码值为 0.01，放大10倍以适配PWM）
# 距离分段基础速度 (注意：下位机为纯PWM后，直接给出PWM百位数值，舍弃factor缩放防止低于物理死区)
BALL_SPEED_FAR: float = 21.4  # 远距离基础速度 (原20.7 * 31/30)
BALL_FACTOR_FAR: float = 1.0     
BALL_SPEED_MID: float = 19.0  # 中距离基础速度 (原18.9 * 31/30)
BALL_FACTOR_MID: float = 1.0     
BALL_SPEED_NEAR: float = 17.6  # 靠近距离基础速度 (原17.1 * 31/30)
BALL_FACTOR_NEAR: float = 1.0    
BALL_SPEED_EXTREME: float = 16.5  # 极近距离基础速度 (原18.05 * 31/30)
BALL_FACTOR_EXTREME: float = 1.0

# 6. 追踪区域 (approach_area) 参数
# PID 控制器参数
TRACK_AREA_KP: float = 0.04  # （原代码值为 0.0055，放大10倍以适配PWM）
TRACK_AREA_KI: float = 0.000  # （原代码值为 0.000）
TRACK_AREA_KD: float = 0.14  # （原代码值为 0.015，放大10倍以适配PWM）
# 距离分段基础速度
AREA_SPEED_FAR: float = 24.8      
AREA_FACTOR_FAR: float = 1.0     
AREA_SPEED_MID: float = 22.2      
AREA_FACTOR_MID: float = 1.0     
AREA_SPEED_NEAR: float = 21.7     
AREA_FACTOR_NEAR: float = 1.0    
AREA_SPEED_EXTREME: float = 18.6  
AREA_FACTOR_EXTREME: float = 1.0 

# 内部数据处理
_origin_label_balls = ["Red_Ball", "Blue_Ball", "Yellow_Ball", "Black_Ball"]
_origin_label_area = ["Blue_Placement_Zone", "Red_Placement_Zone"]
_ball_filter = {"blue": "Red_Ball", "red": "Blue_Ball"}
_area_filter = {"blue": "Red_Placement_Zone", "red": "Blue_Placement_Zone"}

label_balls = [x for x in _origin_label_balls if x != _ball_filter.get(TEAM, "")]
label_area = [x for x in _origin_label_area if x != _area_filter.get(TEAM, "")]

def _validate():
    """参数安全检查"""
    assert TEAM in ("blue", "red"), "队伍必须是 'blue' 或 'red'"

# 初始化时自动校验
_validate()
