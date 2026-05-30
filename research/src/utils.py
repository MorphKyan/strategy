import os
import pathlib
from datetime import datetime
import yaml

def get_project_root():
    """获取项目根目录"""
    return pathlib.Path(__file__).parent.parent

def load_config(config_path=None):
    """加载配置文件"""
    if config_path is None:
        config_path = get_project_root() / 'configs' / 'default.yaml'
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return yaml.safe_load(f)

def setup_results_dir(strategy_name, base_results_dir='results'):
    """创建带时间戳的结果目录"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    results_path = get_project_root() / base_results_dir / strategy_name / timestamp
    results_path.mkdir(parents=True, exist_ok=True)
    return results_path

def save_config_snapshot(config, results_path):
    """在结果目录保存配置副本"""
    with open(results_path / 'config_snapshot.yaml', 'w', encoding='utf-8') as f:
        yaml.dump(config, f, allow_unicode=True)

def set_plot_style():
    """设置绘图样式，支持中文"""
    try:
        import matplotlib.pyplot as plt
        import seaborn as sns
        
        # 设置风格
        sns.set_theme(style="whitegrid")
        
        # 处理中文字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'Arial Unicode MS', 'sans-serif']
        plt.rcParams['axes.unicode_minus'] = False  # 解决负号显示问题
        
        # 设置默认图片大小和分辨率
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['savefig.dpi'] = 300
    except ImportError:
        print("警告: 未安装 matplotlib 或 seaborn，绘图功能将不可用。")
