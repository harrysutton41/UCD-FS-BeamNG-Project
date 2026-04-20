import time
import matplotlib.pyplot as plt
import numpy as np
from beamngpy import BeamNGpy, Scenario, Vehicle, set_up_simple_logging
from beamngpy.sensors import AdvancedIMU
import pandas as pd
import datetime
import os

BEAMNG_HOME = r"C:\Users\Admin\Desktop\BeamNG.tech.v0.37.6.0"
USER_HOME   = r"C:\Users\Admin\AppData\Local\BeamNG\BeamNG.tech"

# ────────────────────────────────────────────────
# CONFIG - CHANGE THIS FOR NEW BATCHES
# ────────────────────────────────────────────────
REF_PATH_FILE = "ref_path.npz"
WAYPOINTS = [
    'DR43_2', 'DR55_37', 'DR48_3', 'DR46_4',
    'DR50_4', 'DR1_61', 'DR55_37', 'DR9_16', 'DR43_2'
]

POLL_INTERVAL = 0.05
MAX_RUNTIME   = 180
SEARCH_WINDOW = 80
CSV_FOLDER    = "run_data"
FINISH_S      = 470.0

DRIVE_MODE = "ai"

# <<< CHANGE ONLY THIS LINE FOR DIFFERENT BATCHES >>>
CONFIGS = ["M3-30"],#["M3-30", "320i", "316i"]#[f"cfg_{i:03d}" for i in range(100, 103)]   # cfg_100 to cfg_109 ["cfg_006"]#

# ────────────────────────────────────────────────
def main():
    set_up_simple_logging()
    bng = BeamNGpy("localhost", 25252, home=BEAMNG_HOME, user=USER_HOME)
    bng.open(launch=True)

    all_paths = []
    summary_data = []

    for config_name in CONFIGS:
        print(f"\n{'='*90}")
        print(f"Starting run for configuration: {config_name}")
        print(f"{'='*90}")

        vehicle = Vehicle(
            "ego_vehicle",
            model="BMW_E36",
            licence="TEST",
            color="Red",
            part_config=f'vehicles/BMW_E36/{config_name}.pc'
        )

        scenario = Scenario("driver_training", f"FS_{config_name}")
        scenario.add_vehicle(vehicle, pos=(-206, 311, 53.093), rot_quat=(0, 0, 0, 0.96))
        scenario.make(bng)

        bng.settings.set_deterministic(60)
        bng.scenario.load(scenario)
        bng.ui.hide_hud()
        bng.scenario.start()

        print("Waiting for vehicle to settle...")
        time.sleep(30)

        print(f"Drive mode: {DRIVE_MODE.upper()}")

        ai_start_time = time.time()
        if DRIVE_MODE == "ai":
            print("Starting AI waypoint driver...")
            vehicle.ai.drive_using_waypoints(
                WAYPOINTS, drive_in_lane=False, avoid_cars=False,
                no_of_laps=1, route_speed=100.0 / 3.6,
                route_speed_mode='limit', aggression=0.95
            )
            time.sleep(0.5)

        # IMUs (unchanged)
        imu_cg = AdvancedIMU("imu_cg", bng, vehicle, pos=(0, 1.25, 0.35), dir=(0, -1, 0), up=(0, 0, 1),
                             gfx_update_time=0.01, physics_update_time=0.005, smoother_strength=2.0,
                             is_using_gravity=True, is_visualised=True, is_snapping_desired=True)

        imu_front = AdvancedIMU("imu_front", bng, vehicle, pos=(0, -1.15, 0.35), dir=(0, -1, 0), up=(0, 0, 1),
                                gfx_update_time=0.01, physics_update_time=0.005, smoother_strength=2.0,
                                is_using_gravity=True, is_visualised=True, is_snapping_desired=True)

        imu_rear = AdvancedIMU("imu_rear", bng, vehicle, pos=(0, 2.25, 0.35), dir=(0, -1, 0), up=(0, 0, 1),
                               gfx_update_time=0.01, physics_update_time=0.005, smoother_strength=2.0,
                               is_using_gravity=True, is_visualised=True, is_snapping_desired=True)

        # Telemetry plot setup
        plt.ion()
        fig, axs = plt.subplots(5, 1, figsize=(10, 12), sharex=True)
        manager = plt.get_current_fig_manager()
        manager.window.wm_geometry("+0+0")
        axs[0].set_ylabel("Speed [m/s]")
        axs[1].set_ylabel("Time [s]")
        axs[2].set_ylabel("Long G CG [g]")
        axs[3].set_ylabel("Lat G CG [g]")
        axs[4].set_ylabel("Δ Vert G (Front – Rear) [g]")
        axs[4].set_xlabel("Position along path s [m]")
        for ax in axs: ax.grid(True)

        line_speed = axs[0].plot([], [], 'b-', lw=2, label="Speed")[0]
        line_time  = axs[1].plot([], [], 'r-', lw=2, label="Lap Time")[0]
        line_long  = axs[2].plot([], [], 'g-', lw=2, label="Long G CG")[0]
        line_lat   = axs[3].plot([], [], 'm-', lw=2, label="Lat G CG")[0]
        line_dvert = axs[4].plot([], [], 'y-', lw=2, label="ΔVert (F-R)")[0]

        for ax in axs: ax.legend()
        fig.suptitle(f"Config: {config_name} — Telemetry vs Path")

        # Reference path
        ref = np.load(REF_PATH_FILE)
        ref_x, ref_y, ref_z, ref_s = ref['x'], ref['y'], ref['z'], ref['s']

        run_data = {'s':[], 'x':[], 'y':[], 'z':[], 'speed_ms':[], 'time_s':[],
                    'long_g_cg':[], 'lat_g_cg':[], 'long_g_front':[], 'vert_g_front':[],
                    'long_g_rear':[], 'vert_g_rear':[]}

        start_time = time.time()
        last_idx = 0
        finished = False

        try:
            while not finished:
                if time.time() - start_time > MAX_RUNTIME:
                    print("Safety timeout reached.")
                    break

                vehicle.sensors.poll()
                state = vehicle.sensors["state"]
                pos = state["pos"]
                speed = np.linalg.norm(state["vel"])
                current_time = time.time() - ai_start_time

                def get_g(imu):
                    data = imu.poll()
                    if data and len(data) > 0:
                        acc = data[0].get('accSmooth', [0.0, 0.0, 0.0])
                        return acc[0]/9.81, acc[1]/9.81, acc[2]/9.81
                    return 0.0, 0.0, 0.0

                long_cg, _, lat_cg = get_g(imu_cg)
                long_f, vert_f, _ = get_g(imu_front)
                long_r, vert_r, _ = get_g(imu_rear)

                # s projection
                ref_points = np.stack([ref_x, ref_y, ref_z], axis=1)
                current_pos = np.array([pos[0], pos[1], pos[2]])
                window_start = max(0, last_idx - 10)
                window_end = min(len(ref_points), last_idx + SEARCH_WINDOW)
                dists = np.linalg.norm(ref_points[window_start:window_end] - current_pos, axis=1)
                idx = window_start + np.argmin(dists)
                s = ref_s[idx]
                last_idx = idx

                # Store
                run_data['s'].append(s)
                run_data['x'].append(pos[0])
                run_data['y'].append(pos[1])
                run_data['z'].append(pos[2])
                run_data['speed_ms'].append(speed)
                run_data['time_s'].append(current_time)
                run_data['long_g_cg'].append(long_cg)
                run_data['lat_g_cg'].append(lat_cg)
                run_data['long_g_front'].append(long_f)
                run_data['vert_g_front'].append(vert_f)
                run_data['long_g_rear'].append(long_r)
                run_data['vert_g_rear'].append(vert_r)

                # Update plot
                line_speed.set_data(run_data['s'], run_data['speed_ms'])
                line_time.set_data(run_data['s'], run_data['time_s'])
                line_long.set_data(run_data['s'], run_data['long_g_cg'])
                line_lat.set_data(run_data['s'], run_data['lat_g_cg'])
                line_dvert.set_data(run_data['s'], [vf - vr for vf, vr in zip(run_data['vert_g_front'], run_data['vert_g_rear'])])

                for ax in axs:
                    ax.relim()
                    ax.autoscale_view()
                fig.canvas.draw()
                fig.canvas.flush_events()

                if len(run_data['s']) % 20 == 0:
                    print(f" s ≈ {s:.1f}m | speed = {speed:.1f} m/s | ΔVert = {vert_f - vert_r:+.3f}g")

                if s >= FINISH_S:
                    print(f"✅ Reached finish line ({FINISH_S}m)")
                    finished = True

                time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            print("\nStopped by user.")
            break

        finally:
            os.makedirs(CSV_FOLDER, exist_ok=True)
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

            df = pd.DataFrame(run_data)
            df = df[df['speed_ms'] > 0.01].reset_index(drop=True)

            csv_path = os.path.join(CSV_FOLDER, f"run_{timestamp}_{config_name}.csv")
            df.to_csv(csv_path, index=False)

            # Save telemetry plot
            fig.savefig(os.path.join(CSV_FOLDER, f"telemetry_{timestamp}_{config_name}.png"), dpi=300, bbox_inches='tight')

            # Save individual path plot
            fig_path, ax_path = plt.subplots(figsize=(10, 8))
            ax_path.plot(df['x'], df['y'], 'b-', lw=2.2, label=config_name)
            ax_path.set_xlabel("X [m]"); ax_path.set_ylabel("Y [m]")
            ax_path.set_title(f"Driven Path - {config_name}")
            ax_path.grid(True); ax_path.axis('equal'); ax_path.legend()
            fig_path.savefig(os.path.join(CSV_FOLDER, f"path_{timestamp}_{config_name}.png"), dpi=300, bbox_inches='tight')
            plt.close(fig_path)
            
            all_paths.append((config_name, df['x'].values, df['y'].values))
            
            #fig_path, ax_path = plt.subplots(figsize=(10, 8))
            #ax_path.plot(df['x'], df['y'], 'b-', lw=2.2, label=config_name)
            #
            #marker_distances = [100, 200, 300, 400]
            #
            #for dist in marker_distances:
            #    idx_marker = (df['s'] - dist).abs().idxmin()
            #    x_marker = df.loc[idx_marker, 'x']
            #    y_marker = df.loc[idx_marker, 'y']
            #
            #    ax_path.plot(x_marker, y_marker, 'ko', markersize=7)
            #    ax_path.text(
            #        x_marker + 1.5, y_marker + 1.5,
            #        f"{dist} m",
            #        fontsize=10,
            #        bbox=dict(facecolor='white', edgecolor='black', pad=2)
            #    )
            #
            #ax_path.set_xlabel("X [m]")
            #ax_path.set_ylabel("Y [m]")
            #ax_path.set_title(f"Driven Path - {config_name}")
            #ax_path.grid(True)
            #ax_path.axis('equal')
            #ax_path.legend()
            #
            #fig_path.savefig(os.path.join(CSV_FOLDER, f"path_{timestamp}_{config_name}.png"),
            #                dpi=300, bbox_inches='tight')
            #plt.close(fig_path)
            
            # ====================== SUMMARY METRICS ======================
            if len(df) > 50 and df['s'].iloc[-1] >= 450:
                lap_time = df['time_s'].iloc[-1]
                avg_speed_kmh = df['speed_ms'].mean() * 3.6
                max_speed_kmh = df['speed_ms'].max() * 3.6
                peak_lat_g = abs(df['lat_g_cg']).max()
                peak_long_g = abs(df['long_g_cg']).max()
                max_delta_vert = abs(df['vert_g_front'] - df['vert_g_rear']).max()
                rms_lat_g = np.sqrt(np.mean(df['lat_g_cg']**2))

                # Section times (0-100, 100-200, ..., 400-470)
                bins = [0, 100, 200, 300, 400, 470]
                labels = ['0-100m', '100-200m', '200-300m', '300-400m', '400-470m']
                df['section'] = pd.cut(df['s'], bins=bins, labels=labels, include_lowest=True, right=True)

                section_times = []
                for sec in labels:
                    sec_df = df[df['section'] == sec]
                    if len(sec_df) > 5:
                        t = sec_df['time_s'].iloc[-1] - sec_df['time_s'].iloc[0]
                        section_times.append(round(t, 3))
                    else:
                        section_times.append(np.nan)

                summary_data.append({
                    'Config': config_name,
                    'Lap_Time_s': round(lap_time, 3),
                    'Avg_Speed_kmh': round(avg_speed_kmh, 2),
                    'Max_Speed_kmh': round(max_speed_kmh, 2),
                    'Peak_Lat_G': round(peak_lat_g, 3),
                    'RMS_Lat_G': round(rms_lat_g, 3),
                    'Peak_Long_G': round(peak_long_g, 3),
                    'Max_|ΔVert_G|': round(max_delta_vert, 3),
                    '0-100m_s': section_times[0],
                    '100-200m_s': section_times[1],
                    '200-300m_s': section_times[2],
                    '300-400m_s': section_times[3],
                    '400-470m_s': section_times[4],
                    'Total_Dist_m': round(df['s'].iloc[-1], 1)
                })

            plt.close(fig)
            bng.scenario.restart()
            time.sleep(1.5)

    # ====================== ALL PATHS OVERLAY ======================
    print("\nCreating final path overlay...")
    fig_overlay, ax_overlay = plt.subplots(figsize=(12, 10))
    colors = plt.cm.tab10(np.linspace(0, 1, len(all_paths)))
    for i, (config_name, x, y) in enumerate(all_paths):
        ax_overlay.plot(x, y, color=colors[i], lw=2.0, label=config_name)
    ax_overlay.set_xlabel("X [m]")
    ax_overlay.set_ylabel("Y [m]")
    ax_overlay.set_title("ALL CONFIGURATIONS — Path Overlay Comparison")
    ax_overlay.grid(True, alpha=0.6)
    ax_overlay.axis('equal')
    ax_overlay.legend(loc='upper right', fontsize=9)
    fig_overlay.savefig(os.path.join(CSV_FOLDER, f"{timestamp}_ALL_PATHS_OVERLAY.png"), dpi=400, bbox_inches='tight')
    plt.close(fig_overlay)
    print("✅ All-paths overlay saved")

    # ====================== SUMMARY TABLE ======================
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_df = summary_df.sort_values(by='Lap_Time_s').reset_index(drop=True)

        summary_csv = os.path.join(CSV_FOLDER, f"{timestamp}_SUMMARY_TABLE.csv")
        summary_df.to_csv(summary_csv, index=False)

        print("\n" + "="*120)
        print("SUMMARY TABLE (sorted by fastest lap time)")
        print("="*120)
        print(summary_df.to_string(index=False))

        # Save table as image
        fig_table, ax_table = plt.subplots(figsize=(14, len(summary_df)*0.45 + 1.5))
        ax_table.axis('off')
        table = ax_table.table(cellText=summary_df.round(3).values,
                               colLabels=summary_df.columns,
                               cellLoc='center', loc='center')
        table.auto_set_font_size(False)
        table.set_fontsize(9)
        table.scale(1.1, 1.8)
        fig_table.savefig(os.path.join(CSV_FOLDER, f"{timestamp}_SUMMARY_TABLE.png"), dpi=350, bbox_inches='tight')
        plt.close(fig_table)

        print(f"\nSummary table saved → {summary_csv}")
        print("Summary table image saved → SUMMARY_TABLE.png")

    bng.ui.show_hud()
    bng.disconnect()
    print("\nBatch completed successfully with full metrics!")

if __name__ == "__main__":
    main()