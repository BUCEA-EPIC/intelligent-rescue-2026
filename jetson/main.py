#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# 文件：main.py
# 功能：智能救援主程序与任务状态机
# 团队：北京建筑大学光启Ray-space工作室

"""
状态机说明:
state 0: 执行寻找球
state 1: 已找到球，执行抓取
state 2: 已抓到球，执行寻找area
state 3: 已找到area，执行放球和后续操作
"""

import cv2
from ultralytics import YOLO
import time
import atexit
import web_server
from control import Controller
from vision import VideoStream, VISION
from config import (
    label_balls, label_area, RESCUE_MODEL, DEFAULT_RESOLUTION, HOLDING_AREA, CENTER_REGION, READY_AREA,
    CATCH_AREA, CROSS_CENTER_REGION, TEAM, _ball_filter,
    SPEED_SEARCH_BALL, SPEED_SEARCH_AREA, SPEED_STUCK_BACKWARD, SPEED_STUCK_TURN,
    SPEED_STUCK_AREA_BACKWARD, SPEED_STUCK_AREA_TURN, SPEED_BLIND_DASH,
    SPEED_DISCARD_TURN, SPEED_DISCARD_BACKWARD,
    SPEED_STATE3_DASH, SPEED_STATE3_BACKWARD, SPEED_STATE3_TURN,
    RELEASE_FORWARD_TIME, RELEASE_BACKWARD_TIME, RELEASE_TURN_TIME
)

model = YOLO(str(RESCUE_MODEL))
model.to('cuda:0')  # 使用GPU推理

stream = VideoStream(save_output=False)
controller = Controller()
vision = VISION(model, label_balls, label_area)

frame_width, frame_height = DEFAULT_RESOLUTION

# 创建视频窗口
# cv2.namedWindow("Rescue Robot Vision", cv2.WINDOW_NORMAL)
# cv2.resizeWindow("Rescue Robot Vision", frame_width, frame_height)

state: int = 0
state_list = ["执行寻找球", "已找到球，执行抓取", "已抓到球，执行寻找area", "已找到area，执行放球和后续操作"]

# 抓取动作的冷却时间戳
catch_cooldown_until = 0.0

# 视觉防卡死脱困变量
stuck_start_time = 0.0
last_target_y = 0.0
ball_lost_start_time = 0.0  # 记录球丢失的开始时间
area_lost_start_time = 0.0  # 记录安全区丢失的开始时间
area_continuous_visible_start = 0.0  # 记录安全区连续可见的开始时间

# 状态2突进防连发标志
has_dashed = False


# 初始化参数
start_flag = 0
frame_count = 0
detect_interval = 2  # 每x帧进行一次检测
start_time = None
results = None  # 存储模型检测结果
running = True
last_flag_found_ball = False
last_flag_found_area = False
last_time = time.time()
last_cmd = None  # 记录上一次的串口命令，用于检测边缘触发
first_catch = True  # 标记是否是第一次抓取
# 追踪爪子状态
claw_state = "open"  # "open"或"close"
holding_confirmed = False  # 记录单次抓取是否已确认
valid_ball_count = 0
wrong_ball_count = 0
first_valid_ball_frame = 0
first_wrong_ball_frame = 0

def is_ball_center_in_area(ball_center, area_box):
    if ball_center is None or area_box is None:
        return False

    x, y = ball_center
    ax1, ay1, ax2, ay2 = area_box

    # 检查球中心是否在安全区域
    return (ax1 <= x <= ax2 and
            ay1 <= y <= ay2)

# 检测球体是否在抓取后位置
def is_ball_in_holding_area(ball_center):
    if ball_center is None:
        return False

    x, y = ball_center
    return (HOLDING_AREA[0] <= x <= HOLDING_AREA[2] and
            HOLDING_AREA[1] <= y <= HOLDING_AREA[3])

print("准备就绪，正在清理摄像头开局残影...")
for _ in range(5):
    try:
        stream.read_frame()
    except Exception:
        pass
system_start_time = time.time()  # 记录程序启动时间

# 启动网页画面传输与遥测服务器
web_server.start_server(host='0.0.0.0', port=8080)
atexit.register(web_server.stop_server)
while running:

    # 读取帧
    frame = stream.read_frame()
    frame_count += 1

    # 处理帧并显示状态
    display_frame = frame.copy()

    if frame_count % detect_interval == 0:
        results = model(frame, verbose=False)

    # 不断从串口读取cmd的值
    # 按键1 -> 0 -> 暂停状态
    # 按键2 -> 1 -> 运行状态
    # 按键3 -> 2 -> 重置状态，注意重置后需要手动按下按键1进入运行状态
    cmd = controller.get_latest_cmd()

    # 检测从其他状态切换到运行状态
    if last_cmd != 0xBB and cmd == 0xBB:
        print("收到启动指令，准备执行【蒙眼出新手村】战术...")
        for _ in range(5):
            try:
                stream.read_frame()
            except Exception:
                pass
                
        # 强制盲目前冲，驶离巨大的同色起跑半圆区域，防止误识别
        print("【战术机动】正在以 1900 的速度驶离起跑区...")
        controller.forward(1900)
        time.sleep(1.5)
        controller.stop()
        time.sleep(0.1)  # 等车身完全停稳
        
        # 冲刺期间可能又积攒了少许帧，排空2帧
        for _ in range(2):
            try:
                stream.read_frame()
            except Exception:
                pass
                
        system_start_time = time.time()  # 驶离起点后，正式重置启动时间（用于防卡死等逻辑）

    last_cmd = cmd

    if cmd == 0xAA:  # 按钮 1：暂停状态
        controller.stop()
        continue
        
    elif cmd == 0xBB:  # 按钮 3 收到指令，执行原按钮 2 的“运行”功能
        pass
        
    elif cmd == 0xCC:  # 按钮 2（已坏）：原来按钮 3 的重置功能挪给它，直接雪藏
        controller.stop()
        controller.release()
        state = 0
        
        print("收到重置指令，正在清理摄像头残留残影...")
        for _ in range(5):
            try:
                stream.read_frame()
            except Exception:
                pass
                
        # 硬件重置时清空状态变量
        system_start_time = time.time()  # 重启时重置开局保护期计时器
        first_catch = True
        stuck_start_time = 0.0
        ball_lost_start_time = 0.0
        area_lost_start_time = 0.0
        area_continuous_visible_start = 0.0
        has_dashed = False
        start_time = None
        last_flag_found_ball = False
        last_flag_found_area = False
        catch_cooldown_until = 0.0
        claw_state = "open"
        holding_confirmed = False
        valid_ball_count = 0
        wrong_ball_count = 0
        first_valid_ball_frame = 0
        first_wrong_ball_frame = 0
        system_start_time = time.time()  # 硬件重置也刷新启动时间
        
        continue

    # 每0.5s打印一次当前状态
    current_time = time.time()
    if current_time > last_time + 0.5:
        last_time = current_time
        print(f"第{frame_count}次运行。当前状态：{state_list[state]}，爪子状态：{claw_state}")

    if start_flag == 0:
        controller.start_catch()
        start_flag = 1

    # 执行寻找球
    if state == 0:
        # 确保爪子是松开的
        if claw_state != "open":
            controller.release()
            claw_state = "open"
            time.sleep(0.3)  # 等待释放完成

        # 2. 检测目标球
        flag_found_ball, ball_data = vision.detect_closest_ball(results)

        if flag_found_ball:
            ball_lost_start_time = 0.0  # 只要看到球，丢失计时器立刻清零

            if not last_flag_found_ball:
                last_flag_found_ball = True
                controller.stop()
                time.sleep(0.1)  # 转圈过程中发现目标立刻停车0.1秒防延迟
                # ball_disappear_counter = 0  # 重置消失计数器

            # 解包ball_data获取坐标数据
            bcx, bcy = ball_data['center']


            # 视觉停滞防卡死
            # 如果目标的 Y 坐标在 3秒内 移动不到 20 个像素，说明车轮在空转，底盘卡在边框了！
            if current_time - system_start_time > 3.0:  # 开局3秒内不触发防卡死
                if abs(bcy - last_target_y) < 20:
                    if stuck_start_time == 0.0:
                        stuck_start_time = time.time()  # 开始卡死计时
                    elif time.time() - stuck_start_time > 5.0:  # 忍耐极限：5秒
                        print("【防卡死触发】找球时底盘物理卡滞！执行倒车甩头脱困！")
                        controller.stop()
                        controller.backward(SPEED_STUCK_BACKWARD)  # 猛倒车拔出来
                        time.sleep(1.5)
                        controller.right(SPEED_STUCK_TURN)  # 往右甩头改变切入角度
                        time.sleep(1.0)
                        controller.stop()
                        
                        # 重置状态，重新开始找
                        stuck_start_time = 0.0
                        last_target_y = 0.0
                        continue 
                else:
                    # 如果 Y 坐标有明显变化，说明在正常靠近，重置计时器并锚定新的 Y 坐标
                    stuck_start_time = 0.0
                    last_target_y = bcy
            else:
                stuck_start_time = 0.0
                last_target_y = bcy



            # 在爪子内，执行抓取
            if vision.is_ready_to_catch(bcx, bcy):
                # 检查是否度过了放球后的冷却期
                if time.time() > catch_cooldown_until:
                    state = 1
                    stuck_start_time = 0.0  # 状态切换，清零防卡死计时器
                else:
                    # 还在冷却中，打印提示，但不切换状态，继续保持state 0
                    print("技能冷却中... 强行忽略眼前的球！")
            else:
                # 如果没在抓取区域，且在冷却期间，依然可以执行追踪靠近
                controller.approach_ball(bcx, bcy)
                
        else:
            controller.search_ball(speed=SPEED_SEARCH_BALL)  # 没找到球，旋转车体进行寻找
            last_flag_found_ball = False

            # 目标丢失容错
            if ball_lost_start_time == 0.0:
                ball_lost_start_time = time.time()  # 记录开始丢失的时刻
            elif time.time() - ball_lost_start_time > 1.0:
                # 丢失超过 1.0 秒，确认不是模型闪烁，而是彻底飞出视野，清空防卡死计时
                stuck_start_time = 0.0

            # 增加消失计数
            # ball_disappear_counter += 1

    # 已找到球，执行抓取
    if state == 1:
        # 如果是首次进入状态1，执行抓取动作
        if claw_state == "open":
            controller.catch()
            claw_state = "close"  # 更新爪子状态
            start_time = time.time()  # 记录抓取开始时间（将作为 state 2 的检测计时器）
            stuck_start_time = 0.0  # 每次闭合爪子立刻清零防卡死计时器
            print("执行抓取动作，立刻进入寻找区域状态进行动态检测")
            
            holding_confirmed = False  # 开启本次抓取的动态检测期
            check_stage = 1  # 分3个阶段，0.5s, 1.0s, 1.5s
            has_dashed = False  # 重置盲冲标志
            state = 2
            stuck_start_time = 0.0  # 状态切换，清零防卡死计时器

    # 已抓到球，执行寻找area
    if state == 2:
        # 动态抓取检测逻辑 (前1.5秒)
        elapsed = time.time() - start_time if start_time else 0
        
        if not holding_confirmed:  # 还在检测期
            target_time = check_stage * 0.5  # 分别在 0.5秒, 1.0秒, 1.5秒 触发
            
            if elapsed >= target_time and check_stage <= 3:
                print(f"【动态检测】到达 {target_time} 秒，开始连抽 5 帧进行第 {check_stage} 次确认...")
                stage_passed = False
                wrong_ball_detected = False
                wrong_ball_label = ""
                
                expected_color = "Blue_Ball" if TEAM == "blue" else "Red_Ball"
                avoid_color = _ball_filter.get(TEAM, "")
                
                for _ in range(5):
                    try:
                        f = stream.read_frame()
                        res = model(f, verbose=False)
                        
                        valid_this_frame = False
                        wrong_this_frame = False
                        
                        for r in res:
                            for box in r.boxes:
                                conf = box.conf[0].item()
                                cls = int(box.cls[0].item())
                                label = model.names[cls]
                                
                                if label in ["Red_Ball", "Blue_Ball", "Yellow_Ball", "Black_Ball"] and conf > vision.min_confidence:
                                    x1, y1, x2, y2 = box.xyxy[0].cpu().numpy().tolist()
                                    center_x, center_y = (x1 + x2) / 2, (y1 + y2) / 2
                                    
                                    if is_ball_in_holding_area((center_x, center_y)):
                                        if first_catch:
                                            if label == expected_color:
                                                valid_this_frame = True
                                            else:
                                                wrong_this_frame = True
                                                wrong_ball_label = label
                                        else:
                                            if label != avoid_color:
                                                valid_this_frame = True
                                            else:
                                                wrong_this_frame = True
                                                wrong_ball_label = label
                        
                        if valid_this_frame:
                            stage_passed = True
                            break  # 只要有一帧合规，直接通过本次检测！
                        elif wrong_this_frame:
                            wrong_ball_detected = True
                    except Exception:
                        pass
                
                if stage_passed:
                    print(f"【动态检测】第 {check_stage} 次确认通过！")
                    if check_stage == 3:
                        print("【动态检测】3次检测（共1.5秒）全部通过，球体锁定成功！")
                        holding_confirmed = True
                        first_catch = False
                    else:
                        check_stage += 1
                else:
                    if wrong_ball_detected:
                        print(f"【动态检测】第 {check_stage} 次确认失败！抓到错球({wrong_ball_label})，执行抛弃！")
                        controller.stop()
                        controller.release()
                        time.sleep(0.3)
                        controller.right(SPEED_DISCARD_TURN)
                        time.sleep(1.2)
                        controller.stop()
                        controller.backward(SPEED_DISCARD_BACKWARD)
                        time.sleep(1.0)
                        controller.stop()
                    else:
                        print(f"【动态检测】第 {check_stage} 次确认失败！未看到目标球，松爪重试！")
                        controller.stop()
                        controller.release()
                        time.sleep(0.3)
                    
                    claw_state = "open"
                    state = 0
                    stuck_start_time = 0.0
                    start_time = None
                    continue


        # 寻找安全区
        flag_found_area, area_data = vision.detect_area(results)

        # 寻找区域
        if flag_found_area:
            area_lost_start_time = 0.0  # 只要看到区域，丢失计时器立刻清零
            
            # 连续可见性确认，避免检测闪烁影响盲冲
            if area_continuous_visible_start == 0.0:
                area_continuous_visible_start = time.time()
            elif time.time() - area_continuous_visible_start > 1.5:
                # 连续锁定超过1.5秒，认为是真锁定，不断重置盲冲计时器
                start_time = time.time()

            if not last_flag_found_area:
                last_flag_found_area = True
                controller.stop()
                print("【稳定检测】旋转中首次发现安全区，微停 0.1 秒防画面拖影...")
                time.sleep(0.1)
                # 抛弃当前这帧因为晃动可能模糊的画面，直接跳出本次循环，下一帧重新确认
                continue

            acx, acy = area_data['center']


            # 视觉停滞防卡死
            if current_time - system_start_time > 3.0:  # 开局3秒内不触发防卡死
                if abs(acy - last_target_y) < 20:
                    if stuck_start_time == 0.0:
                        stuck_start_time = time.time()
                    elif time.time() - stuck_start_time > 5.0:
                        print("【防卡死触发】找安全区时底盘物理卡滞！执行倒车甩头脱困！")
                        controller.stop()
                        controller.backward(SPEED_STUCK_AREA_BACKWARD)
                        time.sleep(1.2)
                        controller.left(SPEED_STUCK_AREA_TURN)  # 找区时可以往反方向(左)甩头
                        time.sleep(0.7)
                        controller.stop()
                        
                        stuck_start_time = 0.0
                        last_target_y = 0.0
                        continue
                else:
                    stuck_start_time = 0.0
                    last_target_y = acy
            else:
                stuck_start_time = 0.0
                last_target_y = acy



            controller.approach_area(acx, acy)

            # 检查安全区中心是否在指定区域
            if (CENTER_REGION[0] <= acx <= CENTER_REGION[2] and
                    CENTER_REGION[1] <= acy <= CENTER_REGION[3]):
                print("安全区位于指定区域，进入状态3")
                state = 3
                stuck_start_time = 0.0  # 状态切换，清零防卡死计时器
                state3_start_time = time.time()  # 记录状态3开始时间
                controller.stop()  # 先停止移动
        else:
            # 没找到区域，原地旋转寻找
            controller.search_area(speed=SPEED_SEARCH_AREA)
            last_flag_found_area = False
            
            # 目标丢失容错
            if area_lost_start_time == 0.0:
                area_lost_start_time = time.time()
            elif time.time() - area_lost_start_time > 1.0:
                stuck_start_time = 0.0
                area_continuous_visible_start = 0.0  # 彻底丢失，清空真锁定计时器
                
                # 2.5圈超时突进逻辑 (这里假设2.5圈是6秒，你必须实车掐表测一下然后改这个值)
            # 修改为可重复触发的技能：每隔8秒盲冲一次
            if start_time and (time.time() - start_time > 8.0):
                print("【战术机动】旋转两周半仍未发现目标，强行盲目前进1.5秒拉近距离！")
                controller.stop()
                time.sleep(0.1)
                    
                # 盲目前冲破坏死角
                controller.forward(SPEED_BLIND_DASH)
                time.sleep(1.5)
                controller.stop()
                    
                time.sleep(0.3)  # 停顿等画面稳定
                    
                start_time = time.time()  # 重置计时器，让它原地继续边转边找

    # 已到达area，执行放球和后续操作
    if state == 3:
        # 超时检查
        if time.time() - state3_start_time > 8:
            print("状态3超时（8秒），强制松爪后退")
            controller.release()
            claw_state = "open"
            controller.backward(SPEED_STUCK_AREA_BACKWARD)  # 用 1200 这个参数
            time.sleep(3)
            controller.stop()
            state = 0
            stuck_start_time = 0.0  # 状态切换，清零防卡死计时器
            continue

        # 1. 前冲
        print(f"执行前冲{RELEASE_FORWARD_TIME}秒")
        controller.forward(SPEED_STATE3_DASH)  # 前进
        time.sleep(RELEASE_FORWARD_TIME)
        controller.stop()

        # 2. 放球并后退
        print("停止0.2秒")
        time.sleep(0.2)

        controller.release()
        claw_state = "open"
        controller.backward(SPEED_STATE3_BACKWARD)
        time.sleep(RELEASE_BACKWARD_TIME)
        controller.stop()
        
        print("停止0.2秒")
        time.sleep(0.2)

        # 3. 转身180°避开已放置区域
        print("放球完毕，后退完成，开始转身180°")
        controller.left(SPEED_STATE3_TURN)  # 转身离开
        time.sleep(RELEASE_TURN_TIME)  # 旋转180°
        controller.stop()  # 停止转身，防止拖影并且在静止状态启动找球



        # 清空一下上一帧的残留记忆
        flag_found_ball = False 
        ball_data = None

        # 强制设置 1 秒的冷却期！
        # 在未来的 1 秒内，不管系统看到什么天王老子，都绝对不允许触发抓取！
        catch_cooldown_until = time.time() + 1


        state = 0
        stuck_start_time = 0.0  # 状态切换，清零防卡死计时器

    # 绘制YOLO检测结果并获取最终标注帧
    annotated_frame = VideoStream.draw_results(frame, results)

    # 准备抓取区域
    cv2.rectangle(
        annotated_frame,
        (CATCH_AREA[0], CATCH_AREA[1]),
        (CATCH_AREA[2], CATCH_AREA[3]),
        (255, 255, 255),  # 白色边框
        2
    )

    # 绘制中部中间区域
    cv2.rectangle(
        annotated_frame,
        (CENTER_REGION[0], CENTER_REGION[1]),
        (CENTER_REGION[2], CENTER_REGION[3]),
        (0, 255, 255),  # 黄色边框
        2
    )

    # 绘制抓取后球体位置检测区域
    cv2.rectangle(
        annotated_frame,
        (HOLDING_AREA[0], HOLDING_AREA[1]),
        (HOLDING_AREA[2], HOLDING_AREA[3]),
        (255, 0, 0),  # 蓝色边框
        2
    )

    # 如果检测到球体，显示其位置
    if state in [2, 3] and flag_found_ball and ball_data:
        ball_center = ball_data['center']
        cv2.circle(annotated_frame, (int(ball_center[0]), int(ball_center[1])), 10, (0, 0, 255), -1)

    # 更新网络画面流与遥测属性
    web_server.update_frame(annotated_frame)
    state_str = state_list[state] if state < len(state_list) else f"未知状态 {state}"
    web_server.update_status(
        state=state_str,
        claw_state=claw_state,
        cmd=cmd if cmd is not None else 0xAA,
        team=TEAM
    )

    # 保存画面帧
    stream.save_frame(annotated_frame)
    # if cv2.waitKey(1) == ord('q'):break

# cv2.destroyAllWindows()
stream.release()
controller.close()
web_server.stop_server()
