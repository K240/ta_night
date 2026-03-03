from __future__ import annotations

from pathlib import Path
from typing import Any
from pxr import Usd, UsdGeom, Gf
import unreal


def resolve_default_layout_path() -> Path:
    return Path(__file__).resolve().parent.parent / "layout.usda"

def vec3_to_list(value: Any) -> list[float]:
    return [float(value[0]), float(value[1]), float(value[2])]


def quat_to_list(value: Any) -> list[float]:
    imaginary = value.GetImaginary()
    return [
        float(value.GetReal()),
        float(imaginary[0]),
        float(imaginary[1]),
        float(imaginary[2]),
    ]

def decompose_matrix(matrix: Gf.Matrix4d):
    position = matrix.ExtractTranslation()
    (success, scaleOrientation, scale, rotation, \
        translation, projection) = matrix.Factor()    
    
    rotation_matrix = rotation.RemoveScaleShear()
    
    rotate_quat = rotation_matrix.ExtractRotationQuat()
    
    return position, rotate_quat, scale

def collect_point_instancer_data( layout_path: Path ) -> list[dict[str, Any]]:
    stage = Usd.Stage.Open(str(layout_path))
    if stage is None:
        raise FileNotFoundError(f"Failed to open USD stage: {layout_path}")

    point_instancers: list[dict[str, Any]] = []
    for prim in stage.Traverse():
        if not prim.IsA(UsdGeom.PointInstancer):
            continue

        instancer = UsdGeom.PointInstancer(prim)
        prototypes: list[dict[str, Any]] = []
        relation = prim.GetRelationship("prototypes")
        targets = relation.GetTargets() if relation and relation.IsValid() else []
        for target in targets:
            prototype_prim = stage.GetPrimAtPath(target)
            if prototype_prim and prototype_prim.IsValid():
                name = prototype_prim.GetName()
                content_path = prototype_prim.GetCustomDataByKey("content_path")
            else:
                name = target.pathString.rsplit("/", 1)[-1]
                content_path = None

            prototypes.append(
                {
                    "name": name,
                    "path": target.pathString,
                    "content_path": content_path,
                }
            )

        proto_indices = instancer.GetProtoIndicesAttr().Get() or []
        instancer_data: dict[str, Any] = {
            "name": prim.GetName(),
            "path": prim.GetPath().pathString,
            "prototypes": prototypes,
            "instance_count": len(proto_indices),
        }

        transforms = instancer.ComputeInstanceTransformsAtTime(
            Usd.TimeCode.Default(),
            Usd.TimeCode.Default(),
            UsdGeom.PointInstancer.ExcludeProtoXform,
        )


        placements_by_asset: dict[tuple[str, Any], dict[str, Any]] = {}
        for index, proto_index in enumerate(proto_indices):
            proto_index_int = int(proto_index)
            prototype_name = (
                prototypes[proto_index_int]["name"]
                if 0 <= proto_index_int < len(prototypes)
                else "<invalid_proto_index>"
            )
            prototype_content_path = (
                prototypes[proto_index_int]["content_path"]
                if 0 <= proto_index_int < len(prototypes)
                else None
            )
            transform = transforms[index] if index < len(transforms) else None
            position, rotate_quat, scale = decompose_matrix(transform)
            asset_key = (prototype_name, prototype_content_path)
            if asset_key not in placements_by_asset:
                placements_by_asset[asset_key] = {
                    "name": prototype_name,
                    "content_path": prototype_content_path,
                    "xforms": [],
                }

            placements_by_asset[asset_key]["xforms"].append(
                {
                    "pos": vec3_to_list(position),
                    "orient": quat_to_list(rotate_quat),
                    "scale": vec3_to_list(scale),
                }
            )

        instancer_data["placements"] = list(placements_by_asset.values())

        point_instancers.append(instancer_data)

    return point_instancers



def clear_all_level_actors() -> int:
    editor_actor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    actors = editor_actor_subsystem.get_all_level_actors()

    deleted_count = 0
    for actor in actors:
        try:
            if editor_actor_subsystem.destroy_actor(actor):
                deleted_count += 1
        except Exception:
            # 削除不可のActorがいても処理は継続する
            continue

    return deleted_count


def create_or_load_level(level_path: str) -> bool:
    level_exists = unreal.EditorAssetLibrary.does_asset_exist(level_path)

    level_subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)

    if level_exists is False:
        success = level_subsystem.new_level(level_path)
        if success is False:
            return False

    success = level_subsystem.load_level(level_path)
    if success is False:
        return False

    if level_exists:
        deleted_count = clear_all_level_actors()
        unreal.log(f"Cleared {deleted_count} actors from existing level: {level_path}")

    return True

def convert_xform_usd_to_unreal(T, R, S):
    unit_scale = 100.0      # m -> cm
    # Translation
    location = unreal.Vector(
        T[0] * unit_scale,
        T[2] * unit_scale,
        T[1] * unit_scale
    )
    # Rotation
    unreal_quat = unreal.Quat(
        -R[1], 
        -R[3], 
        -R[2], 
        R[0]
    )
    rotation = unreal_quat.rotator()
    # Scale3D
    scale = unreal.Vector(
        S[0],
        S[2],
        S[1]
    )
    return location, rotation, scale

def create_or_update_staticMeshActor(instancer, asset_folder='/Game', folder='/'):
    for placement in instancer.get("placements", []):
        actor_name = placement['name']
        asset_path = f"{asset_folder}/{placement['content_path']}"
        xforms = placement['xforms']
        for i, xform in enumerate(xforms):
            location, rotation, scale = convert_xform_usd_to_unreal(xform['pos'], xform['orient'], xform['scale'])

            sm_actor_name = f"{actor_name}_{i:03d}"

            static_mesh = unreal.load_asset(asset_path)
        
            if not static_mesh:
                print(f"Failed to load mesh: {asset_path}")
                continue
            
            editor_subsystem = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
            spawned_actor = editor_subsystem.spawn_actor_from_class(
                unreal.StaticMeshActor,
                location,
                rotation
            )
            
            actor_folder = f"{folder}/{actor_name}"
            spawned_actor.set_actor_label(sm_actor_name)
            spawned_actor.set_actor_scale3d(scale)
            if actor_folder:
                spawned_actor.set_folder_path(actor_folder)
            
            static_mesh_component = spawned_actor.static_mesh_component
            if static_mesh_component:
                static_mesh_component.set_static_mesh(static_mesh)
            else:
                components = spawned_actor.get_components_by_class(unreal.StaticMeshComponent)
                if components:
                    components[0].set_static_mesh(static_mesh)


import tkinter as tk
from tkinter import filedialog

def open_level_file():
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True)

    # ファイル選択ダイアログの表示
    file_path = filedialog.askopenfilename(
        title="Select Layout File",
        filetypes=[("USD File", "*.usda"), ("USD File", "*.usd")],
        parent=root
    )

    if not file_path:
        unreal.log_warning("File selection was canceled.")
        root.destroy()
        return None, None
    else:
        unreal.log(f"Selected Layout File: {file_path}")
        
    root.destroy()
    
    return Path(file_path).stem, file_path

def main() -> None:
    level_name, layout_path = open_level_file()
    if not level_name or not layout_path:
        return

    point_instancers = collect_point_instancer_data(Path(layout_path))

    create_or_load_level(f"/Game/Maps/{level_name}")

    for instancer in point_instancers:
        create_or_update_staticMeshActor(instancer)


if __name__ == "__main__":
    main()
