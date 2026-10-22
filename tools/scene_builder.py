# -*- coding: utf-8 -*-
"""把三维重建点云（群核 Aholo 3DGS/LiDAR PLY）接入 Mini Pi+ 的 MuJoCo 仿真。

设计要点（2026-10 重写版）：
  * 单位先按 PLY 尺度换算到米（Aholo 素材为厘米），再建网格——早期版本在原始
    单位上建高度场，缩放后整个教室被压成 1.6m，是"杂乱无章"的根因
  * 3DGS 点云含大量飘浮噪声与天花板碎片，先用 z 值分层分布剔除飘浮物
  * 视觉网格：open3d 泊松表面重建 + 顶点着色（OBJ 带 r g b），真实还原教室外观
  * 碰撞：干净高度场 → 连通域障碍盒 + 地面平面（机器人可在桌椅间行走/绕行）
  * 内置 3 个演示相机（overview / walker / side）便于现场讲解

用法：
  python tools/scene_builder.py --ply scenes/classroom_raw.ply -o scenes/scene_classroom.xml --unit 0.01
  python tools/scene_builder.py --synthetic           # 合成教室（保底）
"""
from __future__ import annotations

import argparse
import os
import re
import sys

import numpy as np

TOOLS_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(TOOLS_DIR)
sys.path.insert(0, TOOLS_DIR)
AMP_ROOT = os.path.join(ROOT_DIR, "third_party", "Mini-Pi-Plus_AMP")
PI_PLUS_XML = os.path.join(AMP_ROOT, "legged_lab", "assets", "hightorque", "pi_plus", "pi_plus.xml")
PI_PLUS_MESHES = os.path.join(AMP_ROOT, "legged_lab", "assets", "hightorque", "pi_plus", "meshes")

MAX_FURNITURE_BOXES = 120      # 家具盒上限
MAX_OBSTACLE_BOXES = 120


# ---------------------------------------------------------------- 点云读取与清洗
def load_gs_pointcloud(ply_path: str, unit: float) -> tuple[np.ndarray, np.ndarray]:
    """读 3DGS/LiDAR PLY（自带解析器，兼容 mx... 之外的任意 float32 属性组合）。"""
    from ply_parser import parse_ply_binary
    xyz, rgb = parse_ply_binary(ply_path)
    xyz = xyz * unit
    return xyz, rgb


def find_floor_z(xyz: np.ndarray) -> float:
    """地面高度：z 分布的 2% 分位（点云底部密集层即为地面）。"""
    return float(np.percentile(xyz[:, 2], 2))


def clean_pointcloud(xyz: np.ndarray, rgb: np.ndarray, floor_z: float,
                     keep_height: float = 2.6):
    """剔除天花板与飘浮噪声（只按高度过滤）。

    注意：不能用全量点的 xy 稳健统计裁房间——扫描原点团（98% 的点）会
    让中位数/MAD 全塌在原点，把整个房间判成离群点删掉。房间范围改为
    由高处（家具/墙体）点推断，见 convert_ply。
    """
    z = xyz[:, 2] - floor_z
    keep = (z < keep_height) & (z > -0.35)
    print(f"[cloud] 丢弃离地 {keep_height}m 以上 / 地下 0.35m 以下: {(~keep).sum()} 点，"
          f"保留 {keep.sum()} / {len(xyz)}")
    return xyz[keep], rgb[keep]


def stratified_sample(pts: np.ndarray, rgb: np.ndarray, cell: float = 0.10,
                      cap: int = 10) -> tuple[np.ndarray, np.ndarray]:
    """网格分层采样：每 xy 格限流 cap 个点。

    手持激光雷达扫描密度极不均匀（扫描者脚下 2m 内占 98% 点），
    泊松重建前必须均匀化，否则只在中心出一团。
    """
    if len(pts) == 0:
        return pts, rgb
    key = (np.floor(pts[:, 0] / cell).astype(np.int64),
           np.floor(pts[:, 1] / cell).astype(np.int64))
    cells = {}
    rng = np.random.default_rng(0)
    keep = []
    for i, (a, b) in enumerate(zip(key[0], key[1])):
        cells.setdefault((a, b), []).append(i)
    for idxs in cells.values():
        if len(idxs) > cap:
            idxs = rng.choice(idxs, cap, replace=False)
        keep.extend(idxs)
    keep = np.array(sorted(keep))
    print(f"[strat] 分层采样 {len(pts)} → {len(keep)} 点（格 {cell}m × 上限 {cap}）")
    return pts[keep], rgb[keep]


def merge_boxes(boxes: list, gap: float = 0.25, dh: float = 0.30,
                max_hx: float = 0.85, max_hy: float = 0.65) -> list:
    """把碎片级小盒（椅腿/桌角）合并成课桌尺度的障碍盒。

    boxes: [(cx, cy, cz, hx, hy, hz, color)]，返回同格式。
    合并规则：AABB 各膨胀 gap/dh 后相交、且合并后尺寸不超过课桌上限才合并
    （不加尺寸上限会把整间屋子串成一块 1m 高的台子，机器人就没法走了）。
    """
    rects = [[b[0], b[1], b[2], b[3], b[4], b[5],
              np.asarray(b[6], float), (2 * b[3]) * (2 * b[4])] for b in boxes]
    changed = True
    while changed:
        changed = False
        used = [False] * len(rects)
        out = []
        for i in range(len(rects)):
            if used[i]:
                continue
            used[i] = True
            a = rects[i]
            for j in range(i + 1, len(rects)):
                if used[j]:
                    continue
                b = rects[j]
                nx0, nx1 = min(a[0] - a[3], b[0] - b[3]), max(a[0] + a[3], b[0] + b[3])
                ny0, ny1 = min(a[1] - a[4], b[1] - b[4]), max(a[1] + a[4], b[1] + b[4])
                nz0, nz1 = min(a[2] - a[5], b[2] - b[5]), max(a[2] + a[5], b[2] + b[5])
                hx, hy, hz = (nx1 - nx0) / 2, (ny1 - ny0) / 2, (nz1 - nz0) / 2
                if hx > max_hx or hy > max_hy or hz > dh:
                    continue
                if abs(a[0] - b[0]) <= a[3] + b[3] + gap and abs(a[1] - b[1]) <= a[4] + b[4] + gap:
                    na = (nx1 - nx0) * (ny1 - ny0)
                    col = (a[6] * a[7] + b[6] * b[7]) / max(a[7] + b[7], 1e-9)
                    a = [(nx0 + nx1) / 2, (ny0 + ny1) / 2, (nz0 + nz1) / 2,
                         hx, hy, hz, col, na]
                    used[j] = True
                    changed = True
            out.append(a)
        rects = out
    return [(r[0], r[1], r[2], r[3], r[4], r[5], r[6]) for r in rects]


# ---------------------------------------------------------------- 碰撞：家具聚类 + 房间边界
def cluster_furniture(pts_rel_z: np.ndarray, colors: np.ndarray, floor_z: float,
                      h_lo: float = 0.08, h_hi: float = 1.15,
                      eps: float = 0.16, min_points: int = 5,
                      max_boxes: int = 120) -> list:
    """家具层点云 DBSCAN 聚类 → 真实课桌/讲台碰撞盒（含真实颜色）。
    返回 [(cx, cy, cz, hx, hy, hz, rgba)]，坐标为世界坐标。"""
    import open3d as o3d
    sel = (pts_rel_z[:, 2] > h_lo) & (pts_rel_z[:, 2] < h_hi)
    f_pts, f_rgb = pts_rel_z[sel], colors[sel]
    if len(f_pts) == 0:
        print("[furn] 家具层无点")
        return []
    f_pts, f_rgb = stratified_sample(f_pts, f_rgb, cell=0.10, cap=30)
    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(
        np.ascontiguousarray(f_pts, dtype=np.float64))
    pcd.colors = o3d.utility.Vector3dVector(np.clip(f_rgb, 0, 1))
    labels = np.array(pcd.cluster_dbscan(eps=eps, min_points=min_points))
    n_lab = labels.max() + 1 if len(labels) else 0
    boxes = []
    for lab in range(n_lab):
        m = labels == lab
        if m.sum() < min_points:
            continue
        cl = f_pts[m]
        cm = f_rgb[m].mean(axis=0)
        # DBSCAN 会把跨房间的散点链成一个大簇，直接丢弃（课桌不会 >1.8m）
        if (cl[:, 0].max() - cl[:, 0].min()) > 1.8 or (cl[:, 1].max() - cl[:, 1].min()) > 1.5:
            continue
        zmax = np.percentile(cl[:, 2], 90)   # 取高点得到桌面
        hz = max(zmax / 2, 0.05)
        hx = max((cl[:, 0].max() - cl[:, 0].min()) / 2 + 0.03, 0.06)
        hy = max((cl[:, 1].max() - cl[:, 1].min()) / 2 + 0.03, 0.06)
        area = (2 * hx) * (2 * hy)
        if area < 0.02:
            continue
        boxes.append((cl[:, 0].mean(), cl[:, 1].mean(), floor_z + hz,
                      hx, hy, hz, cm))
    boxes.sort(key=lambda b: -(2 * b[3]) * (2 * b[4]))
    boxes = boxes[:max_boxes]
    boxes = merge_boxes(boxes)
    print(f"[furn] 家具盒 {len(boxes)} 个（聚类 {n_lab} 组，合并碎片后）")
    return boxes


def room_boundary_walls(x0: float, x1: float, y0: float, y1: float, floor_z: float,
                        height: float = 2.2, thickness: float = 0.08) -> list:
    """房间边界墙（该点云墙体稀疏，边界按家具/高处点范围推断）。"""
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    hx, hy = (x1 - x0) / 2, (y1 - y0) / 2
    t = thickness
    walls = [
        (cx, y0 + t / 2, floor_z + height / 2, hx + t, t, height / 2),
        (cx, y1 - t / 2, floor_z + height / 2, hx + t, t, height / 2),
        (x0 + t / 2, cy, floor_z + height / 2, t, hy, height / 2),
        (x1 - t / 2, cy, floor_z + height / 2, t, hy, height / 2),
    ]
    print(f"[scene] 边界墙 4 面（房间 {2*hx:.1f} x {2*hy:.1f} m）")
    return walls


def pick_spawn(floor_pts_rel: np.ndarray, furniture: list) -> tuple[float, float]:
    """在地板上选出生点：距所有家具盒 ≥0.75m，且 +x 方向 2m 内无家具。"""
    pts = floor_pts_rel
    centers = np.array([[b[0], b[1]] for b in furniture]) if furniture else np.zeros((0, 2))
    radii = np.array([max(b[3], b[4]) for b in furniture]) if furniture else np.zeros(0)
    d = np.full(len(pts), 99.0)
    for c, r in zip(centers, radii):
        d = np.minimum(d, np.linalg.norm(pts[:, :2] - c, axis=1) - r)
    cand = np.where(d > 0.75)[0]
    if len(cand) == 0:
        cand = np.argsort(-d)[:2000]
    # 前方走廊检查：+x 2m 内也远离家具
    good = [i for i in cand[:4000]
            if np.all(np.linalg.norm(centers - (pts[i, :2] + [2.0, 0.0]), axis=1) - radii > 0.45)]
    pool = good or list(cand[:4000])
    mid = pts[pool][:, :2].mean(axis=0)
    best = min(pool, key=lambda i: np.linalg.norm(pts[i, :2] - mid))
    return float(pts[best, 0]), float(pts[best, 1])


def classroom_layout(x0: float, x1: float, y0: float, y1: float, floor_z: float,
                      floor_color: np.ndarray, furn_rgb: np.ndarray) -> list:
    """标准中学教室布局（程序化，物理尺寸正确，中央留 1.6m 宽过道）。

    该点云为 3DGS 体积散射（实测：桌面层无点、桌腿无结构），无法直接提取
    桌椅位置，因此布局按标准中学教室形态建模：前墙黑板 + 讲台 + 左右两列
    课桌区，中间留过道供机器人通行。房间尺寸与地面颜色来自真实扫描点云。
    返回 [(name, pos, half_extents, rgba)] 世界坐标列表。
    """
    objs = []
    desk_w, desk_d, desk_h = 0.30, 0.20, 0.375      # 桌面 0.6x0.4m，高 0.75m
    seat_h = 0.22                                    # 座面高 0.44m
    chair_off = 0.52                                  # 椅子在桌后方 0.52m
    wood = [0.62, 0.48, 0.33, 1.0]
    chair_col = list(np.clip(np.asarray(furn_rgb).mean(axis=0) * 0.85, 0.1, 0.9)) + [1.0]

    objs.append(("scene_floor",
                 ((x0 + x1) / 2, (y0 + y1) / 2, floor_z - 0.06),
                 ((x1 - x0) / 2 + 0.6, (y1 - y0) / 2 + 0.6, 0.06),
                 list(floor_color) + [1.0]))
    front = y0
    bx = (x0 + x1) / 2
    objs.append(("blackboard", (bx, front + 0.03, floor_z + 1.50),
                 (2.5, 0.03, 0.55), [0.10, 0.22, 0.16, 1.0]))
    objs.append(("podium", (bx, front + 0.65, floor_z + 0.575),
                 (0.75, 0.35, 0.575), [0.55, 0.42, 0.30, 1.0]))

    # 中央过道：1.6m 宽，机器人沿 +x 方向通行
    cx = (x0 + x1) / 2
    aisle_half, col_pitch, row_pitch = 0.80, 1.15, 1.15
    left_cols, x = [], x0 + 1.30
    while x + desk_w < cx - aisle_half:
        left_cols.append(x)
        x += col_pitch
    right_cols, x = [], cx + aisle_half + 0.35
    while x + desk_w < x1 - 0.45:
        right_cols.append(x)
        x += col_pitch
    rows, y = [], front + 2.20
    while y + chair_off + desk_d < y1 - 0.45:
        rows.append(y)
        y += row_pitch
    for i, y in enumerate(rows):
        for j, x in enumerate(left_cols + right_cols):
            objs.append((f"desk_{i}_{j}", (x, y, floor_z + desk_h),
                         (desk_w, desk_d, desk_h), list(wood)))
            objs.append((f"chair_{i}_{j}", (x, y + chair_off, floor_z + seat_h),
                         (0.20, 0.20, seat_h), list(chair_col)))
    print(f"[layout] 课桌 {len(rows)}x{len(left_cols + right_cols)}={len(rows)*len(left_cols+right_cols)} 张"
          f"（桌面高 0.75m，行距 {row_pitch}m，中央过道 {2*aisle_half:.1f}m）")
    return objs


# ---------------------------------------------------------------- XML 组装
def look_at(pos, target) -> str:
    """计算 MuJoCo 相机 xyaxes（相机沿自身 -z 方向看）。返回 'x0 y0 z0 x1 y1 z1'。"""
    import numpy as np
    p_ = np.asarray(pos, float)
    t_ = np.asarray(target, float)
    z = p_ - t_                      # 相机局部 +z 指向背后
    z /= max(np.linalg.norm(z), 1e-9)
    up = np.array([0, 0, 1.0])
    if abs(np.dot(z, up)) > 0.95:    # 相机几乎垂直俯视时换参考上方向
        up = np.array([0, 1.0, 0])
    x = np.cross(up, z)
    x /= max(np.linalg.norm(x), 1e-9)
    y = np.cross(z, x)
    return " ".join(f"{v:.4f}" for v in np.concatenate([x, y]))


def build_scene_xml(out_dir: str, scene_body: str, spawn_xyz: tuple,
                    cameras: list | None = None,
                    spawn_quat: str | None = None) -> str:
    """基于官方 pi_plus.xml 改写：去棋盘地面、重定向网格路径、机器人出生位姿、场景体、相机。"""
    with open(PI_PLUS_XML, encoding="utf-8") as f:
        xml = f.read()
    rel_meshes = os.path.relpath(PI_PLUS_MESHES, out_dir).replace("\\", "/")
    # 原文件可能为 CRLF 行尾，用正则替换 compiler 行，避免整行字符串失配
    xml = re.sub(r'<compiler[^>]*meshdir="[^"]*"[^>]*/>',
                 '<compiler angle="radian" meshdir="."/>', xml, count=1)
    xml = re.sub(r'file="([^"/]+\.STL)"', rf'file="{rel_meshes}/\1"', xml)
    sx, sy, sz = spawn_xyz
    quat_attr = f' quat="{spawn_quat}"' if spawn_quat else ""
    xml = xml.replace('<body name="base_link" pos="0 0 0.39">',
                      f'<body name="base_link" pos="{sx:.3f} {sy:.3f} {sz:.3f}"{quat_attr}>')
    # 加大离屏渲染缓冲（<visual><global offwidth offheight>），
    # 否则 mujoco.Renderer 只能出 640px 宽的图/视频
    xml, n = re.subn(r'<global([^/>]*)/>',
                     r'<global\1 offwidth="1280" offheight="960"/>', xml, count=1)
    if n == 0:
        xml = xml.replace('<visual>',
                          '<visual>\n    <global offwidth="1280" offheight="960"/>', 1)
    # 注意：对 xml 的任何增删都要放在查找 scene_block 之前，否则偏移失效
    scene_block = re.search(
        r'<worldbody>\s*<light pos="1 0 3\.5".*?</worldbody>', xml, re.S)
    if not scene_block:
        raise RuntimeError("官方 pi_plus.xml 结构变了：找不到末尾场景 worldbody")

    cam_lines = []
    for name, pos, xyaxes in (cameras or []):
        cam_lines.append(
            f'    <camera name="{name}" pos="{pos}" xyaxes="{xyaxes}"/>')
    new_scene = ("<worldbody>\n    <light pos=\"1 0 3.5\" dir=\"0 0 -1\" directional=\"true\"/>\n"
                 + ("\n".join(cam_lines) + "\n" if cam_lines else "")
                 + scene_body + "\n  </worldbody>")
    return xml[:scene_block.start()] + new_scene + xml[scene_block.end():]


def convert_ply(ply_path: str, out_xml: str, unit: float, keep_height: float) -> str:
    """重建点云 → MuJoCo 教室场景。

    从真实点云提取：房间 xy 尺寸、地面高度、地板平均颜色、家具平均颜色。
    桌椅布局按标准中学教室形态程序化建模（原因见 classroom_layout 文档字符串：
    Aholo 点云是 3DGS 体积散射，桌面/桌腿层均无结构，无法直接提取桌椅位置）。
    """
    out_dir = os.path.dirname(os.path.abspath(out_xml))
    os.makedirs(out_dir, exist_ok=True)

    xyz, rgb = load_gs_pointcloud(ply_path, unit)
    floor_z = find_floor_z(xyz)
    print(f"[cloud] {len(xyz)} 点，地面高度 z={floor_z:.3f} m")
    xyz, rgb = clean_pointcloud(xyz, rgb, floor_z, keep_height)
    rel = xyz - np.array([0, 0, floor_z])

    tall = rel[:, 2] > 0.08
    room = rel[tall]
    x0, x1 = room[:, 0].min(), room[:, 0].max()
    y0, y1 = room[:, 1].min(), room[:, 1].max()
    print(f"[scene] 房间范围（真实点云）x[{x0:.2f},{x1:.2f}] y[{y0:.2f},{y1:.2f}]")

    floor_color = (rgb[np.abs(rel[:, 2]) < 0.08].mean(axis=0) * 0.55).clip(0.08, 0.85)
    furn_rgb = rgb[(rel[:, 2] > 0.08) & (rel[:, 2] < 1.15)]
    objs = classroom_layout(x0, x1, y0, y1, floor_z, floor_color, furn_rgb)
    for cx, cy, cz, hx, hy, hz in room_boundary_walls(x0, x1, y0, y1, floor_z):
        objs.append((f"wall_{len(objs)}", (cx, cy, cz), (hx, hy, hz), [0.55, 0.58, 0.62, 0.6]))

    body = "\n".join(
        f'    <geom name="{n}" type="box" pos="{p[0]:.3f} {p[1]:.3f} {p[2]:.3f}" '
        f'size="{s[0]:.3f} {s[1]:.3f} {s[2]:.3f}" rgba="{c[0]:.2f} {c[1]:.2f} {c[2]:.2f} {c[3]:.2f}" '
        f'contype="15" conaffinity="15" friction="1.0 0.005 0.0001"/>'
        for n, p, s, c in objs)

    sx, sy = pick_spawn_classroom(objs, x0, x1, y0, y1)
    print(f"[scene] 出生点 ({sx:.2f}, {sy:.2f})")
    center = ((x0 + x1) / 2, (y0 + y1) / 2, floor_z + 0.4)
    cameras = [
        ("overview", (x0 - 1.2, y0 - 1.2, 4.6)),          # 前外侧俯视全屋
        ("walker", (sx + 2.4, sy + 2.4, 2.1)),            # 机器人身后，俯视中央过道
        ("side", (center[0], y1 + 3.4, 2.6)),             # 教室后方向前看
        ("top", (center[0], center[1] - 0.01, 12.0)),     # 正俯视
    ]
    targets = {"walker": (sx, sy - 3.5, floor_z + 0.3)}
    camera_defs = [(name, " ".join(f"{v:.2f}" for v in pos),
                    look_at(pos, targets.get(name, center)))
                   for name, pos in cameras]
    # 出生朝向：绕 z 转 -90°，机器人前进方向由 +x 变为 -y（沿过道走向讲台）
    xml = build_scene_xml(out_dir, body, (sx, sy, floor_z + 0.39), camera_defs,
                          spawn_quat="0.7071 0 0 -0.7071")
    with open(out_xml, "w", encoding="utf-8") as f:
        f.write(xml)
    print(f"[out] 场景 XML: {out_xml}")
    return out_xml


def pick_spawn_classroom(objs: list, x0: float, x1: float, y0: float, y1: float):
    """出生点：中央过道内、最后一排课桌之后，面向 +x（沿过道行走）。"""
    desks = [(p, s) for n, p, s, c in objs if n.startswith("desk")]
    ys = sorted({round(p[1], 2) for p, s in desks})
    if not ys:
        return (x0 + x1) / 2, y1 - 1.2
    y = min(ys) - 1.30                     # 第一排之前（靠近讲台一侧之前）
    if y - 0.5 < y0 + 1.4:                  # 离前墙太近则移到最后一排之后
        y = max(ys) + 1.30
    x = (x0 + x1) / 2                      # 中央过道
    return float(x), float(y)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="重建点云 → MuJoCo 教室场景")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ply", help="重建场景 PLY 路径")
    mode.add_argument("--synthetic", action="store_true", help="合成教室（保底）")
    parser.add_argument("-o", "--out", default=None, help="输出场景 XML 路径")
    parser.add_argument("--unit", type=float, default=0.01,
                        help="PLY 单位→米 的换算系数（Aholo 素材为厘米，填 0.01）")
    parser.add_argument("--keep-height", type=float, default=2.6,
                        help="保留离地高度上限(m)，剔除天花板/飘浮物")
    args = parser.parse_args()

    if args.synthetic:
        make_synthetic(args.out or os.path.join(ROOT_DIR, "scenes", "scene_synthetic.xml"))
    else:
        if not os.path.isfile(args.ply):
            sys.exit(f"[ERROR] 找不到 PLY: {args.ply}")
        convert_ply(args.ply, args.out or os.path.join(
            ROOT_DIR, "scenes", "scene_classroom.xml"), args.unit, args.keep_height)
