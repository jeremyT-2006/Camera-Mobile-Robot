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
    parser.add_argument("--network", type=str, default="ssd-mobilenet-v1", help="AI Model: ssd-mobilenet-v1 (Fastest, 25-30 FPS) or ssd-mobilenet-v2")
    parser.add_argument("--threshold", type=float, default=0.45, help="Detection confidence threshold")
    parser.add_argument("--width", type=int, default=1280, help="Camera capture width")
    parser.add_argument("--height", type=int, default=720, help="Camera capture height")
    parser.add_argument("--rate", type=int, default=30, help="Camera framerate")
    parser.add_argument("--headless", action="store_true", help="Run without graphical display for max FPS")
    parser.add_argument("--frame-skip", type=int, default=1, help="Inference every N frames (1=every frame, 2=every 2nd frame)")
    parser.add_argument("--kp", type=float, default=1.2, help="Proportional steering gain Kp")
    return parser.parse_args()

def main():
    args = parse_args()

    print("=" * 65)
    print("  HIGH-PERFORMANCE OBSTACLE AVOIDANCE SYSTEM (JETSON NANO)")
    print(f"  Model       : {args.network}")
    print(f"  Resolution  : {args.width}x{args.height} @ {args.rate} FPS")
    print(f"  Headless    : {args.headless}")
    print(f"  Frame Skip  : {args.frame_skip}")
    print(f"  Steering Kp : {args.kp}")
    print("=" * 65)

    cam_options = [
        f"--input-width={args.width}",
        f"--input-height={args.height}",
        f"--input-rate={args.rate}"
    ]
    camera = jetson.utils.videoSource(args.input, argv=cam_options)
    if camera is None:
        print(f"[ERROR] Cannot open camera: {args.input}")
        sys.exit(1)

    display = None
    font = None
    if not args.headless:
        display = jetson.utils.videoOutput("display://0")
        font = jetson.utils.cudaFont(size=22)

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
    zone_left = w / 3.0
    zone_right = 2.0 * w / 3.0

    frame_count = 0
    fps_history = []
    last_detections = []
    robot_action = "FORWARD"
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
                overlay_flag = "none" if args.headless else "box,labels,conf"
                detections = net.Detect(img, overlay=overlay_flag)
                last_detections = detections
            else:
                detections = last_detections
            t_infer = time.time() - t1

            t2 = time.time()
            robot_action = "FORWARD"
            v_lin = 0.3
            w_ang = 0.0
            steer_error = 0.0
            nearest_dist_est = 999.0

            hazard_detected = False
            for det in detections:
                box_h = det.Height
                box_cx = det.Center[0]

                dist_est = (fx * 0.5) / max(box_h, 1.0)
                if dist_est < nearest_dist_est:
                    nearest_dist_est = dist_est

                if box_h > (h * 0.22):
                    hazard_detected = True
                    steer_error = (box_cx - cx_ref) / fx
                    w_ang = -args.kp * steer_error

                    if zone_left <= box_cx <= zone_right:
                        robot_action = "STOP / EVADE"
                        v_lin = 0.0
                        w_ang = 1.0 if box_cx < cx_ref else -1.0
                        break
                    elif box_cx < zone_left:
                        robot_action = "TURN RIGHT"
                        v_lin = 0.15
                    elif box_cx > zone_right:
                        robot_action = "TURN LEFT"
                        v_lin = 0.15

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
                hud_text = f"ACTION: {robot_action} | V:{v_lin:.2f} W:{w_ang:.2f} | FPS: {avg_fps:.1f}"
                font.OverlayText(img, text=hud_text, x=15, y=h - 40, color=(0, 255, 0, 255), background=(0, 0, 0, 180))

                display.SetStatus(f"[{args.network}] FPS: {avg_fps:.1f} | Action: {robot_action}")
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
