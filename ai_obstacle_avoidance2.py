import argparse
import sys
import time

try:
    import jetson.inference
    import jetson.utils
except ImportError:
    try:
        import jetson_inference as jetson_inference_lib
        import jetson_utils as jetson_utils_lib
        class JetsonContainer:
            inference = jetson_inference_lib
            utils = jetson_utils_lib
        jetson = JetsonContainer()
    except ImportError:
        print("[ERROR] jetson.inference / jetson.utils not found on system.")
        sys.exit(1)

def parse_args():
    parser = argparse.ArgumentParser(description="High-FPS Obstacle Avoidance for Jetson Nano")
    parser.add_argument("--input", type=str, default="csi://0", help="Camera input URI (e.g. csi://0)")
    parser.add_argument("--network", type=str, default="ssd-mobilenet-v1", help="AI Model: ssd-mobilenet-v1 (Fastest) or ssd-mobilenet-v2")
    parser.add_argument("--threshold", type=float, default=0.45, help="Detection confidence threshold")
    parser.add_argument("--width", type=int, default=640, help="Camera capture width (default 640)")
    parser.add_argument("--height", type=int, default=480, help="Camera capture height (default 480)")
    parser.add_argument("--rate", type=int, default=30, help="Camera framerate")
    parser.add_argument("--flip", type=str, default="none", choices=["none", "rotate-180", "horizontal", "vertical"], help="Camera flip")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display for max FPS")
    parser.add_argument("--frame-skip", type=int, default=1, help="Inference every N frames (1=every frame, 2=every 2nd frame)")
    parser.add_argument("--kp", type=float, default=1.2, help="Proportional steering gain Kp")
    return parser.parse_args()

def draw_bbox_lines(img, x1, y1, x2, y2, color, thickness=2):
    try:
        jetson.utils.cudaDrawLine(img, (x1, y1), (x2, y1), color, thickness)
        jetson.utils.cudaDrawLine(img, (x2, y1), (x2, y2), color, thickness)
        jetson.utils.cudaDrawLine(img, (x2, y2), (x1, y2), color, thickness)
        jetson.utils.cudaDrawLine(img, (x1, y2), (x1, y1), color, thickness)
    except Exception:
        pass

def main():
    args = parse_args()

    print("=" * 65)
    print("  HIGH-PERFORMANCE OBSTACLE AVOIDANCE SYSTEM (JETSON NANO)")
    print(f"  Model       : {args.network}")
    print(f"  Resolution  : {args.width}x{args.height} @ {args.rate} FPS")
    print(f"  Camera Flip : {args.flip}")
    print(f"  Headless    : {args.headless}")
    print(f"  Frame Skip  : {args.frame_skip}")
    print("=" * 65)

    cam_options = [
        f"--input-width={args.width}",
        f"--input-height={args.height}",
        f"--input-rate={args.rate}",
        f"--input-flip={args.flip}"
    ]
    camera = jetson.utils.videoSource(args.input, argv=cam_options)
    if camera is None:
        print(f"[ERROR] Cannot open camera: {args.input}")
        sys.exit(1)

    display = None
    font_main = None
    font_hud = None
    if not args.headless:
        display = jetson.utils.videoOutput("display://0")
        font_main = jetson.utils.cudaFont(size=18)
        font_hud = jetson.utils.cudaFont(size=24)

    print(f"Loading TensorRT engine: {args.network}...")
    try:
        net = jetson.inference.detectNet(args.network, threshold=args.threshold)
    except Exception as e:
        print(f"[ERROR] Failed to load model {args.network}: {e}")
        print("Falling back to ssd-mobilenet-v2...")
        net = jetson.inference.detectNet("ssd-mobilenet-v2", threshold=args.threshold)

    w = args.width
    h = args.height
    cx_ref = w / 2.0
    fx = w * 0.8
    zone_left = int(w // 3)
    zone_right = int(2 * (w // 3))

    COLOR_GREEN = (0, 255, 0, 255)
    COLOR_RED = (255, 0, 0, 255)
    COLOR_YELLOW = (255, 255, 0, 255)
    COLOR_WHITE = (255, 255, 255, 255)
    COLOR_GRAY = (200, 200, 200, 255)
    COLOR_BLACK = (0, 0, 0, 255)

    frame_count = 0
    fps_history = []
    last_detections = []
    robot_action = "FORWARD"
    action_color = COLOR_GREEN
    v_lin = 0.3
    w_ang = 0.0

    t_prev = time.time()

    print("\n[READY] System running. Press Ctrl+C in terminal to stop.\n")

    try:
        while True:
            if display is not None and not display.IsStreaming():
                break

            t0 = time.time()
            img = camera.Capture()
            if img is None:
                continue
            t_cap = time.time() - t0

            frame_count += 1
            do_inference = (frame_count % args.frame_skip == 0)

            t1 = time.time()
            if do_inference:
                detections = net.Detect(img, overlay="none")
                last_detections = detections
            else:
                detections = last_detections
            t_infer = time.time() - t1

            t2 = time.time()
            robot_action = "FORWARD"
            action_color = COLOR_GREEN
            v_lin = 0.3
            w_ang = 0.0
            steer_error = 0.0
            nearest_dist_est = 999.0
            detected_boxes = []

            for det in detections:
                x1 = int(det.Left)
                y1 = int(det.Top)
                x2 = int(det.Right)
                y2 = int(det.Bottom)
                box_cx = int(det.Center[0])
                box_h = int(det.Height)
                label = net.GetClassDesc(det.ClassID)
                conf = det.Confidence

                box_color = COLOR_GREEN
                is_close = box_h > 110

                dist_est = (fx * 0.5) / max(box_h, 1.0)
                if dist_est < nearest_dist_est:
                    nearest_dist_est = dist_est

                if is_close:
                    box_color = COLOR_RED
                    steer_error = (box_cx - cx_ref) / fx
                    w_ang = -args.kp * steer_error

                    if zone_left <= box_cx <= zone_right:
                        robot_action = "STOP / EVADE"
                        action_color = COLOR_RED
                        v_lin = 0.0
                        w_ang = 1.0 if box_cx < cx_ref else -1.0
                    elif box_cx < zone_left and robot_action != "STOP / EVADE":
                        robot_action = "TURN RIGHT"
                        action_color = COLOR_YELLOW
                        v_lin = 0.15
                    elif box_cx > zone_right and robot_action != "STOP / EVADE":
                        robot_action = "TURN LEFT"
                        action_color = COLOR_YELLOW
                        v_lin = 0.15

                detected_boxes.append((x1, y1, x2, y2, box_color, label, conf))

            t_logic = time.time() - t2

            t_now = time.time()
            dt = t_now - t_prev
            t_prev = t_now
            fps_instant = (1.0 / dt) if dt > 0 else 0.0

            fps_history.append(fps_instant)
            if len(fps_history) > 30:
                fps_history.pop(0)
            avg_fps = sum(fps_history) / len(fps_history)

            if display is not None:
                try:
                    jetson.utils.cudaDrawLine(img, (zone_left, 0), (zone_left, h), COLOR_GRAY, 1)
                    jetson.utils.cudaDrawLine(img, (zone_right, 0), (zone_right, h), COLOR_GRAY, 1)
                except Exception:
                    pass

                font_main.OverlayText(img, text="LEFT", x=int(zone_left // 2 - 25), y=15, color=COLOR_GRAY)
                font_main.OverlayText(img, text="CENTER", x=int(w // 2 - 35), y=15, color=COLOR_GRAY)
                font_main.OverlayText(img, text="RIGHT", x=int(zone_right + (w - zone_right) // 2 - 30), y=15, color=COLOR_GRAY)

                for (x1, y1, x2, y2, box_color, label, conf) in detected_boxes:
                    draw_bbox_lines(img, x1, y1, x2, y2, box_color, thickness=2)
                    font_main.OverlayText(img, text=f"{label} {conf:.2f}", x=x1, y=max(y1 - 22, 5), color=box_color)

                try:
                    jetson.utils.cudaDrawRect(img, (0, h - 65, w, h), COLOR_BLACK)
                except Exception:
                    pass

                font_hud.OverlayText(img, text=f"ACTION: {robot_action}", x=20, y=h - 48, color=action_color)
                font_main.OverlayText(img, text=f"FPS: {avg_fps:.1f}", x=w - 140, y=h - 42, color=COLOR_WHITE)

                display.SetStatus(f"MOBILE ROBOT - OBSTACLE AVOIDANCE | FPS: {avg_fps:.1f}")
                display.Render(img)

            if frame_count % 15 == 0:
                net_fps = net.GetNetworkFPS()
                print(f"[METRICS] FPS: {avg_fps:4.1f} (Net: {net_fps:4.1f}) | Cap: {t_cap*1000:4.1f}ms | Infer: {t_infer*1000:4.1f}ms | Action: {robot_action:12s} | Dist: {nearest_dist_est:.2f}m")

    except KeyboardInterrupt:
        print("\n[STOP] User interrupted execution.")

    finally:
        print("[SHUTDOWN] Releasing camera and display resources...")
        del camera
        if display is not None:
            del display
        print("[DONE] Safe exit completed.")

if __name__ == "__main__":
    main()
