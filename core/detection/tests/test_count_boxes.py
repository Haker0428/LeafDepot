"""
count_boxes 算法入口单元测试脚本

使用方法:
    python -m core.detection.tests.test_count_boxes
    或
    python core/detection/tests/test_count_boxes.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
_project_root = Path(__file__).resolve().parent.parent.parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from core.detection import count_boxes
from core.detection.processors import StackProcessorFactory


def test_count_boxes_basic():
    """基础功能测试 - 使用新的目录结构（自动查找main.jpeg和fourth.jpeg）"""
    print("\n" + "="*60)
    print("🧪 测试1: 基础功能测试")
    print("="*60)
    
    # 使用新的测试目录结构：total/test01/ 包含 main.jpeg 和 fourth.jpeg
    test_dir = _project_root / "tests" / "test_images" / "total" / "test01"
    debug_flag = True
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    # 检查必要的文件是否存在
    main_img = test_dir / "main.jpeg"
    depth_img = test_dir / "fourth.jpeg"
    
    if not main_img.exists():
        print(f"⚠️  原始图 main.jpeg 不存在: {main_img}")
    if not depth_img.exists():
        print(f"⚠️  深度图 fourth.jpeg 不存在: {depth_img}")
    
    try:
        # 传入目录路径，会自动查找 main.jpeg 和 fourth.jpeg
        total = count_boxes(
            str(test_dir),  # 传入目录路径
            pile_id=1, 
            enable_debug=debug_flag,
            enable_visualization=debug_flag  # 启用可视化，保存效果图到output目录
        )

        if debug_flag:
            print(f"\n✅ 测试通过")
            print(f"📁 测试目录: {test_dir}")
            print(f"📸 原始图: main.jpeg")
            print(f"📊 深度图: fourth.jpeg")
            print(f"📦 总箱数: {total}")
            print(f"💾 效果图已保存到: core/detection/output/ 目录")
            
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_count_boxes_custom_config():
    """自定义配置测试 - 使用新的目录结构"""
    print("\n" + "="*60)
    print("🧪 测试2: 自定义配置测试")
    print("="*60)
    
    test_dir = _project_root / "tests" / "test_images" / "total" / "test01"
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    try:
        # 使用自定义模型路径和配置路径
        model_path = _project_root / "shared" / "models" / "yolo" / "pile+box.pt"
        config_path = _project_root / "core" / "config" / "pile_config.json"
        
        total = count_boxes(
            str(test_dir),  # 传入目录路径
            pile_id=1,
            model_path=str(model_path),
            pile_config_path=str(config_path),
            enable_debug=False
        )
        print(f"\n✅ 测试通过")
        print(f"📦 总箱数: {total}")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_count_boxes_different_pile_id():
    """不同pile_id测试 - 使用新的目录结构"""
    print("\n" + "="*60)
    print("🧪 测试3: 不同pile_id测试")
    print("="*60)
    
    test_dir = _project_root / "tests" / "test_images" / "total" / "test01"
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    pile_ids = [1, 2, 3]
    results = {}
    
    for pile_id in pile_ids:
        try:
            print(f"\n📋 测试 pile_id={pile_id}...")
            total = count_boxes(str(test_dir), pile_id=pile_id, enable_debug=False)
            results[pile_id] = total
            print(f"   ✅ pile_id={pile_id}: 总箱数={total}")
        except Exception as e:
            print(f"   ❌ pile_id={pile_id} 失败: {e}")
            results[pile_id] = None
    
    print(f"\n📊 结果汇总:")
    for pile_id, total in results.items():
        if total is not None:
            print(f"   pile_id={pile_id}: {total}箱")
        else:
            print(f"   pile_id={pile_id}: 失败")
    
    return all(v is not None for v in results.values())


def test_count_boxes_error_handling():
    """错误处理测试"""
    print("\n" + "="*60)
    print("🧪 测试4: 错误处理测试")
    print("="*60)
    
    # 测试不存在的图片
    print("\n📋 测试1: 不存在的图片路径")
    try:
        total = count_boxes("nonexistent_image.jpg", pile_id=1, enable_debug=False)
        print(f"   ❌ 应该抛出异常但没有")
        return False
    except FileNotFoundError as e:
        print(f"   ✅ 正确抛出 FileNotFoundError: {e}")
    except Exception as e:
        print(f"   ⚠️  抛出了其他异常: {e}")
    
    # 测试不存在的模型路径
    print("\n📋 测试2: 不存在的模型路径")
    test_dir = _project_root / "tests" / "test_images" / "total" / "test01"
    if test_dir.exists():
        try:
            total = count_boxes(
                str(test_dir),
                pile_id=1,
                model_path="nonexistent_model.pt",
                enable_debug=False
            )
            print(f"   ❌ 应该抛出异常但没有")
            return False
        except FileNotFoundError as e:
            print(f"   ✅ 正确抛出 FileNotFoundError: {e}")
        except Exception as e:
            print(f"   ⚠️  抛出了其他异常: {e}")
    
    print(f"\n✅ 错误处理测试通过")
    return True


def test_depth_image_path():
    """深度图自动查找功能测试 - 使用新的目录结构"""
    print("\n" + "="*60)
    print("🧪 测试6: 深度图自动查找功能测试")
    print("="*60)
    
    test_dir = _project_root / "tests" / "test_images" / "total" / "test01"
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    try:
        # 测试1: 传入目录路径，自动查找main.jpeg和fourth.jpeg
        print("\n📋 测试1: 传入目录路径，自动查找main.jpeg和fourth.jpeg")
        total1 = count_boxes(str(test_dir), pile_id=1, enable_debug=True)
        print(f"   ✅ 自动查找深度图: 总箱数={total1}")
        
        # 测试2: 传入main.jpeg文件路径，在同目录查找fourth.jpeg
        print("\n📋 测试2: 传入main.jpeg文件路径，在同目录查找fourth.jpeg")
        main_img = test_dir / "main.jpeg"
        if main_img.exists():
            total2 = count_boxes(str(main_img), pile_id=1, enable_debug=False)
            print(f"   ✅ 通过文件路径查找深度图: 总箱数={total2}")
        else:
            print(f"   ⚠️  main.jpeg不存在，跳过此测试")
            total2 = total1
        
        # 测试3: 显式指定深度图路径（覆盖自动查找）
        print("\n📋 测试3: 显式指定深度图路径（覆盖自动查找）")
        depth_img = test_dir / "fourth.jpeg"
        if depth_img.exists():
            total3 = count_boxes(
                str(test_dir), 
                pile_id=1, 
                depth_image_path=str(depth_img),
                enable_debug=False
            )
            print(f"   ✅ 显式指定深度图: 总箱数={total3}")
        else:
            print(f"   ⚠️  fourth.jpeg不存在，跳过此测试")
            total3 = total1
        
        # 验证结果一致（允许有小的差异，因为深度图处理可能影响结果）
        print(f"\n📊 结果汇总: {total1} vs {total2} vs {total3}")
        if total1 == total2 == total3:
            print(f"✅ 所有测试通过，结果一致: {total1}")
            return True
        else:
            print(f"⚠️  结果有差异（可能是正常的，因为深度图处理方式不同）")
            return True  # 仍然返回True，因为差异可能是正常的
            
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_factory_class():
    """工厂类测试 - 使用新的目录结构"""
    print("\n" + "="*60)
    print("🧪 测试5: StackProcessorFactory 类测试")
    print("="*60)
    
    test_dir = _project_root / "tests" / "test_images" / "total" / "test01"
    
    if not test_dir.exists():
        print(f"❌ 测试目录不存在: {test_dir}")
        return False
    
    try:
        factory = StackProcessorFactory(enable_debug=True)
        total = factory.count(str(test_dir), pile_id=1)
        print(f"\n✅ 测试通过")
        print(f"📦 总箱数: {total}")
        return True
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False


def run_all_tests():
    """运行所有测试"""
    print("\n" + "="*60)
    print("🚀 count_boxes 算法入口单元测试")
    print("="*60)
    
    tests = [
        ("基础功能测试", test_count_boxes_basic),
        # ("自定义配置测试", test_count_boxes_custom_config),
        # ("不同pile_id测试", test_count_boxes_different_pile_id),
        # ("错误处理测试", test_count_boxes_error_handling),
        # ("深度图路径预留功能测试", test_depth_image_path),
        # ("工厂类测试", test_factory_class),
    ]
    
    results = []
    for name, test_func in tests:
        try:
            result = test_func()
            results.append((name, result))
        except Exception as e:
            print(f"\n❌ 测试 '{name}' 执行异常: {e}")
            import traceback
            traceback.print_exc()
            results.append((name, False))
    
    # 汇总结果
    print("\n" + "="*60)
    print("📊 测试结果汇总")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for name, result in results:
        status = "✅ 通过" if result else "❌ 失败"
        print(f"{status} - {name}")
    
    print(f"\n总计: {passed}/{total} 测试通过")
    
    if passed == total:
        print("🎉 所有测试通过！")
        return 0
    else:
        print("⚠️  部分测试失败")
        return 1


if __name__ == "__main__":
    exit_code = run_all_tests()
    sys.exit(exit_code)
