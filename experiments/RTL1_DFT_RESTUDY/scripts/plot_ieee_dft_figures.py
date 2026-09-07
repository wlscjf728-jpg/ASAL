#!/usr/bin/env python3
"""
Generate IEEE Journal single-column figures for AES MixColumns DFT evaluation.
Target: IEEE Transactions style (single column width ~3.5 inches, large font, high contrast).
"""

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# IEEE styling parameters
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'Arial', 'Helvetica']
plt.rcParams['mathtext.fontset'] = 'dejavusans'
plt.rcParams['axes.edgecolor'] = '#333333'
plt.rcParams['axes.linewidth'] = 1.2
plt.rcParams['grid.color'] = '#CCCCCC'
plt.rcParams['grid.linestyle'] = '--'
plt.rcParams['grid.linewidth'] = 0.7

OUTPUT_DIR = Path(__file__).resolve().parents[1] / "reports"
ARTIFACT_DIR = OUTPUT_DIR / "generated_figures"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------------------
# Figure 1: Natural Fault Universe - MC Scan Sweep & Stage Comparison
# Y-axis: Detected Fault Count (개수)
# -------------------------------------------------------------------------
def plot_fig1():
    fig, ax = plt.subplots(figsize=(3.6, 2.8), dpi=300)
    
    mc_ffs = [0, 32, 64, 96, 128]
    stuck_cnt = [2840, 2866, 2896, 2912, 2926]
    trans_cnt = [2346, 2398, 2436, 2470, 2502]
    
    # Lines
    ax.plot(mc_ffs, stuck_cnt, color='#1f77b4', marker='o', markersize=7, linewidth=2.2, label='Stuck-at (72.8k faults)')
    ax.plot(mc_ffs, trans_cnt, color='#d62728', marker='s', markersize=7, linewidth=2.2, label='Transition (72.8k faults)')
    
    # Baselines (Random Mean)
    ax.axhline(2900.2, color='#1f77b4', linestyle=':', linewidth=1.5, alpha=0.85)
    ax.text(2, 2905, 'Random Stuck (2,900)', color='#1f77b4', fontsize=8.5, fontweight='bold')
    
    ax.axhline(2475.2, color='#d62728', linestyle=':', linewidth=1.5, alpha=0.85)
    ax.text(2, 2480, 'Random Trans (2,475)', color='#d62728', fontsize=8.5, fontweight='bold')
    
    ax.set_xlabel('MC Scan Flip-Flops (Count)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Detected Faults (Count)', fontsize=11, fontweight='bold')
    ax.set_xticks(mc_ffs)
    ax.set_xticklabels(['0\n(0%)', '32\n(25%)', '64\n(50%)', '96\n(75%)', '128\n(100%)'], fontsize=9.5)
    ax.tick_params(axis='y', labelsize=10)
    ax.set_ylim(2250, 3050)
    ax.grid(True, alpha=0.45)
    ax.legend(loc='lower right', fontsize=9, framealpha=0.9)
    
    fig.tight_layout()
    svg_path = OUTPUT_DIR / "fig1_natural_fault_sweep.svg"
    png_path = OUTPUT_DIR / "fig1_natural_fault_sweep.png"
    fig.savefig(svg_path, format='svg')
    fig.savefig(png_path, format='png')
    fig.savefig(ARTIFACT_DIR / "fig1_natural_fault_sweep.svg", format='svg')
    fig.savefig(ARTIFACT_DIR / "fig1_natural_fault_sweep.png", format='png')
    plt.close(fig)
    print("Saved Figure 1:", svg_path)

# -------------------------------------------------------------------------
# Figure 2: Structural Cone Attribution (MC_CONE Observability)
# Y-axis: MC_CONE Coverage (%) and Detected Count
# -------------------------------------------------------------------------
def plot_fig2():
    fig, ax1 = plt.subplots(figsize=(3.6, 2.8), dpi=300)
    
    mc_ffs = [0, 32, 64, 96, 128]
    stuck_cov = [0.42, 3.71, 7.14, 10.29, 13.47]
    trans_cov = [0.28, 3.57, 6.47, 9.31, 12.11]
    
    l1 = ax1.plot(mc_ffs, stuck_cov, color='#0066cc', marker='o', markersize=7.5, linewidth=2.4, label='Stuck-at in MC Cone')
    l2 = ax1.plot(mc_ffs, trans_cov, color='#cc0000', marker='^', markersize=7.5, linewidth=2.4, label='Transition in MC Cone')
    
    # Baselines: Random Mean inside MC_CONE
    ax1.axhline(4.31, color='#0066cc', linestyle='--', linewidth=1.5, alpha=0.8)
    ax1.text(3, 4.55, 'Random Stuck (4.3%)', color='#0066cc', fontsize=8.5, fontweight='bold')
    
    ax1.axhline(3.73, color='#cc0000', linestyle='--', linewidth=1.5, alpha=0.8)
    ax1.text(3, 2.7, 'Random Trans (3.7%)', color='#cc0000', fontsize=8.5, fontweight='bold')
    
    ax1.set_xlabel('MC Scan Flip-Flops (Count)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('MC_CONE Coverage (%)', fontsize=11, fontweight='bold')
    ax1.set_xticks(mc_ffs)
    ax1.set_xticklabels(['0', '32', '64', '96', '128'], fontsize=10)
    ax1.tick_params(axis='y', labelsize=10)
    ax1.set_ylim(0, 15.5)
    ax1.grid(True, alpha=0.45)
    
    # Annotate delta at 128 FFs
    ax1.annotate('+9.2%p\n(3.1×)', xy=(128, 13.47), xytext=(103, 13.2),
                 fontsize=8.5, fontweight='bold', color='#0066cc')
    
    ax1.legend(loc='center left', bbox_to_anchor=(0.02, 0.78), fontsize=8.8, framealpha=0.9)
    
    fig.tight_layout()
    svg_path = OUTPUT_DIR / "fig2_cone_attribution.svg"
    png_path = OUTPUT_DIR / "fig2_cone_attribution.png"
    fig.savefig(svg_path, format='svg')
    fig.savefig(png_path, format='png')
    fig.savefig(ARTIFACT_DIR / "fig2_cone_attribution.svg", format='svg')
    fig.savefig(ARTIFACT_DIR / "fig2_cone_attribution.png", format='png')
    plt.close(fig)
    print("Saved Figure 2:", svg_path)

# -------------------------------------------------------------------------
# Figure 3: SB-to-MC Fault-Share Sweep (Sensitivity Comparison)
# -------------------------------------------------------------------------
def plot_fig3():
    fig, ax = plt.subplots(figsize=(3.6, 2.8), dpi=300)
    
    mc_share = [7.85, 20.0, 40.0, 60.0, 80.0]
    mc_cov = [3.81, 5.49, 7.99, 10.76, 13.44]
    rnd_cov = [3.60, 4.11, 4.80, 5.64, 6.53]
    iark_cov = [3.71, 3.73, 3.81, 3.95, 4.10]
    sr_cov = [3.43, 3.46, 3.53, 3.68, 3.83]
    sb_cov = [3.33, 3.31, 3.23, 3.08, 3.08]
    
    ax.plot(mc_share, mc_cov, color='#0055ff', marker='D', markersize=7, linewidth=2.5, label='CASE_MC (+9.6%p)')
    ax.plot(mc_share, rnd_cov, color='#ff6600', marker='o', markersize=6, linewidth=2.0, linestyle='-', label='Random Mean (+2.9%p)')
    ax.plot(mc_share, iark_cov, color='#2ca02c', marker='^', markersize=5.5, linewidth=1.5, linestyle='--', label='CASE_IARK (+0.4%p)')
    ax.plot(mc_share, sr_cov, color='#9467bd', marker='v', markersize=5.5, linewidth=1.5, linestyle='--', label='CASE_SR (+0.4%p)')
    ax.plot(mc_share, sb_cov, color='#8c564b', marker='x', markersize=6, linewidth=1.5, linestyle=':', label='CASE_SB (-0.3%p)')
    
    ax.set_xlabel('MC Fault Share in Universe (%)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Total Test Coverage (%)', fontsize=11, fontweight='bold')
    ax.set_xticks(mc_share)
    ax.set_xticklabels(['7.9%', '20%', '40%', '60%', '80%'], fontsize=9.5)
    ax.tick_params(axis='y', labelsize=10)
    ax.set_ylim(2.5, 14.5)
    ax.grid(True, alpha=0.45)
    ax.legend(loc='upper left', fontsize=8.2, framealpha=0.9)
    
    fig.tight_layout()
    svg_path = OUTPUT_DIR / "fig3_faultshare_sensitivity.svg"
    png_path = OUTPUT_DIR / "fig3_faultshare_sensitivity.png"
    fig.savefig(svg_path, format='svg')
    fig.savefig(png_path, format='png')
    fig.savefig(ARTIFACT_DIR / "fig3_faultshare_sensitivity.svg", format='svg')
    fig.savefig(ARTIFACT_DIR / "fig3_faultshare_sensitivity.png", format='png')
    plt.close(fig)
    print("Saved Figure 3:", svg_path)

# -------------------------------------------------------------------------
# Figure 4: 2D Scan-Share x Fault-Share Interaction Curves
# -------------------------------------------------------------------------
def plot_fig4():
    fig, ax = plt.subplots(figsize=(3.6, 2.8), dpi=300)
    
    mc_scan = [0, 32, 64, 96, 128]
    
    f80 = [4.10, 6.33, 9.23, 11.13, 13.44]
    f60 = [3.95, 5.61, 7.83, 9.08, 10.76]
    f40 = [3.81, 4.76, 6.24, 6.99, 7.99]
    f20 = [3.73, 4.08, 4.91, 5.11, 5.49]
    f08 = [3.71, 3.66, 3.86, 3.74, 3.81]
    
    colors = ['#800026', '#bd0026', '#e31a1c', '#fc4e2a', '#6baed6']
    
    ax.plot(mc_scan, f80, color=colors[0], marker='o', markersize=6.5, linewidth=2.3, label='MC Fault 80% (Δ=+9.3%p)')
    ax.plot(mc_scan, f60, color=colors[1], marker='s', markersize=6.5, linewidth=2.1, label='MC Fault 60% (Δ=+6.8%p)')
    ax.plot(mc_scan, f40, color=colors[2], marker='^', markersize=6.5, linewidth=1.9, label='MC Fault 40% (Δ=+4.2%p)')
    ax.plot(mc_scan, f20, color=colors[3], marker='v', markersize=6.5, linewidth=1.7, label='MC Fault 20% (Δ=+1.8%p)')
    ax.plot(mc_scan, f08, color='#555555', marker='x', markersize=7.0, linewidth=1.8, linestyle='--', label='MC Fault 7.9% (Natural)')
    
    ax.set_xlabel('MC Scan Flip-Flops (Count)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Test Coverage (%)', fontsize=11, fontweight='bold')
    ax.set_xticks(mc_scan)
    ax.set_xticklabels(['0', '32', '64', '96', '128'], fontsize=10)
    ax.tick_params(axis='y', labelsize=10)
    ax.set_ylim(3.0, 14.5)
    ax.grid(True, alpha=0.45)
    ax.legend(loc='upper left', fontsize=8.0, framealpha=0.92)
    
    fig.tight_layout()
    svg_path = OUTPUT_DIR / "fig4_2d_interaction_matrix.svg"
    png_path = OUTPUT_DIR / "fig4_2d_interaction_matrix.png"
    fig.savefig(svg_path, format='svg')
    fig.savefig(png_path, format='png')
    fig.savefig(ARTIFACT_DIR / "fig4_2d_interaction_matrix.svg", format='svg')
    fig.savefig(ARTIFACT_DIR / "fig4_2d_interaction_matrix.png", format='png')
    plt.close(fig)
    print("Saved Figure 4:", svg_path)

# -------------------------------------------------------------------------
# Combined 4-Panel Figure (2x2 Grid for Overview)
# -------------------------------------------------------------------------
def plot_combined():
    fig, axes = plt.subplots(2, 2, figsize=(8.2, 6.4), dpi=300)
    
    # Subplot (a) - Exp 1: Dual Y-Axis to expand both curves
    ax_a1 = axes[0, 0]
    ax_a2 = ax_a1.twinx()
    
    mc_ffs = [0, 32, 64, 96, 128]
    stuck_cnt = [2840, 2866, 2896, 2912, 2926]
    trans_cnt = [2346, 2398, 2436, 2470, 2502]
    
    l1 = ax_a1.plot(mc_ffs, stuck_cnt, color='#1f77b4', marker='o', markersize=6.5, linewidth=2.4, label='Stuck-at (Left)')
    l2 = ax_a2.plot(mc_ffs, trans_cnt, color='#d62728', marker='s', markersize=6.5, linewidth=2.4, label='Transition (Right)')
    
    ax_a1.set_title('(a)', fontsize=14.0, fontweight='bold', pad=8)
    ax_a1.set_xlabel('MC Scan Flip-Flops (Count)', fontsize=11.5, fontweight='bold')
    ax_a1.set_ylabel('Stuck-at Detected (Count)', fontsize=11.5, fontweight='bold', color='#1f77b4')
    ax_a2.set_ylabel('Transition Detected (Count)', fontsize=11.5, fontweight='bold', color='#d62728')
    
    ax_a1.set_xticks(mc_ffs)
    ax_a1.set_xticklabels(['0', '32', '64', '96', '128'], fontsize=10.5)
    # Tilt 4-digit numbers by 30 degrees to reduce horizontal footprint
    ax_a1.tick_params(axis='y', labelcolor='#1f77b4', labelsize=10.0, labelrotation=30)
    ax_a2.tick_params(axis='y', labelcolor='#d62728', labelsize=10.0, labelrotation=-30)
    
    # Expand vertical range so the monotonic increase is pronounced
    ax_a1.set_ylim(2830, 2940)
    ax_a2.set_ylim(2330, 2520)
    ax_a1.grid(True, alpha=0.35)
    
    # Combined legend for (a)
    lines_a = l1 + l2
    labels_a = [l.get_label() for l in lines_a]
    ax_a1.legend(lines_a, labels_a, loc='lower right', fontsize=8.8, framealpha=0.92, borderpad=0.35, labelspacing=0.25)

    # Subplot (b) - Exp 2: Local MC_CONE Observability
    ax_b = axes[0, 1]
    stuck_cov = [0.42, 3.71, 7.14, 10.29, 13.47]
    trans_cov = [0.28, 3.57, 6.47, 9.31, 12.11]
    ax_b.plot(mc_ffs, stuck_cov, color='#0066cc', marker='o', markersize=6.5, linewidth=2.4, label='Stuck in MC_CONE')
    ax_b.plot(mc_ffs, trans_cov, color='#cc0000', marker='^', markersize=6.5, linewidth=2.4, label='Trans in MC_CONE')
    ax_b.set_title('(b)', fontsize=14.0, fontweight='bold', pad=8)
    ax_b.set_xlabel('MC Scan Flip-Flops (Count)', fontsize=11.5, fontweight='bold')
    ax_b.set_ylabel('MC_CONE Coverage (%)', fontsize=11.5, fontweight='bold')
    ax_b.set_xticks(mc_ffs)
    ax_b.set_xticklabels(['0', '32', '64', '96', '128'], fontsize=10.5)
    ax_b.tick_params(axis='y', labelsize=10.5)
    ax_b.set_ylim(0, 16.0)
    ax_b.grid(True, alpha=0.35)
    ax_b.legend(loc='upper left', fontsize=8.8, framealpha=0.92, borderpad=0.35, labelspacing=0.25)

    # Subplot (c) - Exp 3: SB-to-MC Fault Sensitivity (All 5 cases)
    ax_c = axes[1, 0]
    mc_share = [7.85, 20.0, 40.0, 60.0, 80.0]
    mc_cov = [3.81, 5.49, 7.99, 10.76, 13.44]
    rnd_cov = [3.60, 4.11, 4.80, 5.64, 6.53]
    iark_cov = [3.71, 3.73, 3.81, 3.95, 4.10]
    sr_cov = [3.43, 3.46, 3.53, 3.68, 3.83]
    sb_cov = [3.33, 3.31, 3.23, 3.08, 3.08]
    
    ax_c.plot(mc_share, mc_cov, color='#0055ff', marker='D', markersize=6.0, linewidth=2.4, label='CASE_MC (+9.6%p)')
    ax_c.plot(mc_share, rnd_cov, color='#ff6600', marker='o', markersize=5.5, linewidth=2.0, label='Random Mean (+2.9%p)')
    ax_c.plot(mc_share, iark_cov, color='#2ca02c', marker='^', markersize=5.0, linewidth=1.7, linestyle='--', label='CASE_IARK (+0.4%p)')
    ax_c.plot(mc_share, sr_cov, color='#9467bd', marker='v', markersize=5.0, linewidth=1.7, linestyle='--', label='CASE_SR (+0.4%p)')
    ax_c.plot(mc_share, sb_cov, color='#8c564b', marker='x', markersize=5.5, linewidth=1.7, linestyle=':', label='CASE_SB (-0.3%p)')
    
    ax_c.set_title('(c)', fontsize=14.0, fontweight='bold', pad=8)
    ax_c.set_xlabel('MC Fault Share (%)', fontsize=11.5, fontweight='bold')
    ax_c.set_ylabel('Total Coverage (%)', fontsize=11.5, fontweight='bold')
    ax_c.set_xticks(mc_share)
    ax_c.set_xticklabels(['7.9%', '20%', '40%', '60%', '80%'], fontsize=10.5)
    ax_c.tick_params(axis='y', labelsize=10.5)
    ax_c.set_ylim(2.2, 15.8)
    ax_c.grid(True, alpha=0.35)
    ax_c.legend(loc='upper left', fontsize=7.8, framealpha=0.94, handletextpad=0.4, borderpad=0.35, labelspacing=0.22)

    # Subplot (d) - Exp 4: 2D Interaction Curves (All 5 cases)
    ax_d = axes[1, 1]
    mc_scan = mc_ffs
    f80 = [4.10, 6.33, 9.23, 11.13, 13.44]
    f60 = [3.95, 5.61, 7.83, 9.08, 10.76]
    f40 = [3.81, 4.76, 6.24, 6.99, 7.99]
    f20 = [3.73, 4.08, 4.91, 5.11, 5.49]
    f08 = [3.71, 3.66, 3.86, 3.74, 3.81]
    
    colors = ['#800026', '#bd0026', '#e31a1c', '#fc4e2a', '#555555']
    ax_d.plot(mc_scan, f80, color=colors[0], marker='o', markersize=5.5, linewidth=2.2, label='Fault 80% (Δ=+9.3%p)')
    ax_d.plot(mc_scan, f60, color=colors[1], marker='s', markersize=5.5, linewidth=2.0, label='Fault 60% (Δ=+6.8%p)')
    ax_d.plot(mc_scan, f40, color=colors[2], marker='^', markersize=5.5, linewidth=1.8, label='Fault 40% (Δ=+4.2%p)')
    ax_d.plot(mc_scan, f20, color=colors[3], marker='v', markersize=5.5, linewidth=1.6, label='Fault 20% (Δ=+1.8%p)')
    ax_d.plot(mc_scan, f08, color=colors[4], marker='x', markersize=6.0, linewidth=1.7, linestyle='--', label='Fault 7.9% (Natural)')
    
    ax_d.set_title('(d)', fontsize=14.0, fontweight='bold', pad=8)
    ax_d.set_xlabel('MC Scan Flip-Flops (Count)', fontsize=11.5, fontweight='bold')
    ax_d.set_ylabel('Total Coverage (%)', fontsize=11.5, fontweight='bold')
    ax_d.set_xticks(mc_scan)
    ax_d.set_xticklabels(['0', '32', '64', '96', '128'], fontsize=10.5)
    ax_d.tick_params(axis='y', labelsize=10.5)
    ax_d.set_ylim(2.5, 15.5)
    ax_d.grid(True, alpha=0.35)
    ax_d.legend(loc='upper left', fontsize=7.8, framealpha=0.94, handletextpad=0.4, borderpad=0.35, labelspacing=0.22)

    fig.tight_layout()
    svg_path = OUTPUT_DIR / "fig_combined_4panel_dft.svg"
    png_path = OUTPUT_DIR / "fig_combined_4panel_dft.png"
    fig.savefig(svg_path, format='svg')
    fig.savefig(png_path, format='png')
    fig.savefig(ARTIFACT_DIR / "fig_combined_4panel_dft.svg", format='svg')
    fig.savefig(ARTIFACT_DIR / "fig_combined_4panel_dft.png", format='png')
    plt.close(fig)
    print("Saved Combined Figure:", svg_path)

if __name__ == '__main__':
    plot_fig1()
    plot_fig2()
    plot_fig3()
    plot_fig4()
    plot_combined()
    print("All figures successfully generated!")
