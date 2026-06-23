import pandas as pd
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
import matplotlib.pyplot as plt
import matplotlib
import traceback
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# 设置中文字体
matplotlib.rcParams['font.sans-serif'] = ['SimHei']
matplotlib.rcParams['axes.unicode_minus'] = False


class FuzzyPrioritySystem:
    """模糊逻辑优先级排序系统（包含物料齐套率）"""

    def __init__(self):
        """初始化模糊逻辑系统"""
        # 定义模糊变量
        self.amount = ctrl.Antecedent(np.arange(0, 11, 1), '订单金额')  # 0-10
        self.urgency = ctrl.Antecedent(np.arange(0, 101, 1), '剩余天数')  # 0-100
        self.customer_level = ctrl.Antecedent(np.arange(1, 6, 1), '客户等级')  # 1-5
        self.material_readiness = ctrl.Antecedent(np.arange(0, 101, 1), '物料齐套率')  # 0-100
        self.priority = ctrl.Consequent(np.arange(0, 101, 1), '优先级')  # 0-100

        # 定义隶属函数
        self._setup_membership_functions()

        # 定义规则
        self._setup_rules()

        # 创建控制系统
        self.control_system = ctrl.ControlSystem(self.rules)
        self.simulation = ctrl.ControlSystemSimulation(self.control_system)

    def _setup_membership_functions(self):
        """设置隶属函数（低/中/高三级）"""
        # 订单金额隶属函数
        self.amount['低'] = fuzz.trimf(self.amount.universe, [0, 0, 4])
        self.amount['中'] = fuzz.trimf(self.amount.universe, [2, 5, 8])
        self.amount['高'] = fuzz.trimf(self.amount.universe, [6, 10, 10])

        # 剩余天数隶属函数（剩余天数越少，紧急程度越高）
        self.urgency['低'] = fuzz.trimf(self.urgency.universe, [0, 0, 30])  # 紧急度高
        self.urgency['中'] = fuzz.trimf(self.urgency.universe, [10, 50, 90])
        self.urgency['高'] = fuzz.trimf(self.urgency.universe, [70, 100, 100])  # 紧急度低

        # 客户等级隶属函数
        self.customer_level['低'] = fuzz.trimf(self.customer_level.universe, [1, 1, 3])
        self.customer_level['中'] = fuzz.trimf(self.customer_level.universe, [2, 3, 4])
        self.customer_level['高'] = fuzz.trimf(self.customer_level.universe, [3, 5, 5])

        # 物料齐套率隶属函数（越高越好）
        self.material_readiness['低'] = fuzz.trimf(self.material_readiness.universe, [0, 0, 40])
        self.material_readiness['中'] = fuzz.trimf(self.material_readiness.universe, [30, 50, 70])
        self.material_readiness['高'] = fuzz.trimf(self.material_readiness.universe, [60, 100, 100])

        # 优先级隶属函数
        self.priority['低'] = fuzz.trimf(self.priority.universe, [0, 0, 50])
        self.priority['中'] = fuzz.trimf(self.priority.universe, [20, 50, 80])
        self.priority['高'] = fuzz.trimf(self.priority.universe, [60, 100, 100])

    def _setup_rules(self):
        """设置模糊规则（包含物料齐套率）"""
        self.rules = [
            # 高优先级规则：紧急（剩余天数少）且重要（金额高或客户等级高）且物料齐套率高
            ctrl.Rule(self.urgency['低'] & self.amount['高'] & self.material_readiness['高'], self.priority['高']),
            ctrl.Rule(self.urgency['低'] & self.customer_level['高'] & self.material_readiness['高'],
                      self.priority['高']),
            ctrl.Rule(
                self.amount['高'] & self.customer_level['高'] & self.urgency['中'] & self.material_readiness['高'],
                self.priority['高']),

            # 物料齐套率高可提升优先级
            ctrl.Rule(
                self.material_readiness['高'] & (self.urgency['低'] | self.amount['高'] | self.customer_level['高']),
                self.priority['高']),

            # 物料齐套率低会降低优先级
            ctrl.Rule(
                self.material_readiness['低'] & (self.urgency['高'] | self.amount['低'] | self.customer_level['低']),
                self.priority['低']),

            # 中优先级规则：中等紧急或中等重要
            ctrl.Rule(self.urgency['中'] & (self.amount['中'] | self.customer_level['中']), self.priority['中']),
            ctrl.Rule(self.amount['中'] & self.customer_level['中'], self.priority['中']),

            # 物料齐套率中等时保持原优先级
            ctrl.Rule(
                self.material_readiness['中'] & (self.urgency['中'] | self.amount['中'] | self.customer_level['中']),
                self.priority['中']),

            # 低优先级规则：不紧急或不重要
            ctrl.Rule(self.urgency['高'] | self.amount['低'], self.priority['低']),
            ctrl.Rule(self.customer_level['低'] & self.amount['低'], self.priority['低']),

            # 物料齐套率低且其他条件不利时优先级更低
            ctrl.Rule(self.material_readiness['低'] & self.urgency['高'], self.priority['低']),

            # 特殊情况：即使物料齐套率低，但非常紧急或非常重要时仍可提高优先级
            ctrl.Rule(
                self.material_readiness['低'] & self.urgency['低'] & (self.amount['高'] | self.customer_level['高']),
                self.priority['中'])
        ]

    def calculate_priority(self, order_amount, remaining_days, customer_level, material_readiness):
        """计算单个订单的优先级（包含物料齐套率）"""
        # 输入限制
        order_amount = np.clip(order_amount, 0, 10)
        remaining_days = np.clip(remaining_days, 0, 100)
        customer_level = np.clip(customer_level, 1, 5)
        material_readiness = np.clip(material_readiness, 0, 100)

        try:
            # 创建新的模拟实例
            simulation = ctrl.ControlSystemSimulation(self.control_system)

            # 模糊推理
            simulation.input['订单金额'] = order_amount
            simulation.input['剩余天数'] = remaining_days
            simulation.input['客户等级'] = customer_level
            simulation.input['物料齐套率'] = material_readiness
            simulation.compute()

            # 检查output字典中是否有'优先级'键
            if '优先级' in simulation.output:
                return simulation.output['优先级']
            else:
                # 如果没有计算结果，返回默认值50
                return 50
        except Exception as e:
            print(f"计算优先级时发生错误: {e}")
            print(
                f"输入: 订单金额={order_amount}, 剩余天数={remaining_days}, 客户等级={customer_level}, 物料齐套率={material_readiness}")
            traceback.print_exc()
            return 50  # 出错时返回中等优先级

    def calculate_batch_priority(self, df):
        """批量计算订单优先级（包含物料齐套率）"""
        priorities = []

        for idx, row in df.iterrows():
            try:
                priority = self.calculate_priority(
                    row['订单金额'],
                    row['剩余天数'],
                    row['客户等级'],
                    row['物料齐套率']  # 新增物料齐套率参数
                )
                priorities.append(priority)
            except Exception as e:
                print(f"第{idx + 1}行计算错误: {str(e)}")
                priorities.append(50)  # 出错时设为中等优先级

        return np.array(priorities)

    def generate_unique_ranking(self, priorities, break_ties_with=None):
        """
        生成唯一排序（1-n，优先级越高排名越前，不重复）

        Parameters:
        -----------
        priorities : array-like
            优先级得分数组
        break_ties_with : DataFrame, optional
            用于打破平局的辅助数据

        Returns:
        --------
        ranking : ndarray
            唯一排名数组
        """
        priorities = np.array(priorities)

        # 如果提供了用于打破平局的辅助数据
        if break_ties_with is not None:
            # 创建一个包含所有排序依据的DataFrame
            sort_df = pd.DataFrame({
                'priority': priorities,
                'original_index': range(len(priorities))
            })

            # 添加辅助列用于排序
            for i, col in enumerate(break_ties_with.columns):
                sort_df[f'tie_breaker_{i}'] = break_ties_with[col].values

            # 定义排序列（按优先级降序，然后按辅助列排序以确保唯一性）
            sort_columns = ['priority'] + [f'tie_breaker_{i}' for i in range(len(break_ties_with.columns))]

            # 确定排序顺序：优先级降序，其他升序
            ascendings = [False] + [True] * len(break_ties_with.columns)

            # 进行稳定排序
            sort_df = sort_df.sort_values(by=sort_columns, ascending=ascendings)

            # 分配唯一排名
            sort_df['ranking'] = range(1, len(sort_df) + 1)

            # 按原始索引恢复顺序
            sort_df = sort_df.sort_values('original_index')
            return sort_df['ranking'].values.astype(int)

        else:
            # 如果没有提供打破平局的数据，使用稳定排序
            sorted_indices = np.argsort(-priorities, kind='stable')  # 降序稳定排序
            ranking = np.zeros_like(priorities, dtype=int)

            # 分配唯一排名
            for rank, idx in enumerate(sorted_indices, start=1):
                ranking[idx] = rank

            return ranking

    def plot_membership_functions(self):
        """绘制隶属函数（包含物料齐套率）"""
        fig, axes = plt.subplots(3, 2, figsize=(14, 15))

        # 调整子图间距
        plt.subplots_adjust(hspace=0.4, wspace=0.3)

        # 订单金额隶属函数
        axes[0, 0].plot(self.amount.universe, self.amount['低'].mf, 'r', label='低', linewidth=2)
        axes[0, 0].plot(self.amount.universe, self.amount['中'].mf, 'g', label='中', linewidth=2)
        axes[0, 0].plot(self.amount.universe, self.amount['高'].mf, 'b', label='高', linewidth=2)
        axes[0, 0].set_title('订单金额隶属函数')
        axes[0, 0].set_xlabel('订单金额')
        axes[0, 0].set_ylabel('隶属度')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)

        # 剩余天数隶属函数
        axes[0, 1].plot(self.urgency.universe, self.urgency['低'].mf, 'r', label='紧急', linewidth=2)
        axes[0, 1].plot(self.urgency.universe, self.urgency['中'].mf, 'g', label='中', linewidth=2)
        axes[0, 1].plot(self.urgency.universe, self.urgency['高'].mf, 'b', label='宽松', linewidth=2)
        axes[0, 1].set_title('剩余天数隶属函数')
        axes[0, 1].set_xlabel('剩余天数')
        axes[0, 1].set_ylabel('隶属度')
        axes[0, 1].legend()
        axes[0, 1].grid(True, alpha=0.3)

        # 客户等级隶属函数
        axes[1, 0].plot(self.customer_level.universe, self.customer_level['低'].mf, 'r', label='低', linewidth=2)
        axes[1, 0].plot(self.customer_level.universe, self.customer_level['中'].mf, 'g', label='中', linewidth=2)
        axes[1, 0].plot(self.customer_level.universe, self.customer_level['高'].mf, 'b', label='高', linewidth=2)
        axes[1, 0].set_title('客户等级隶属函数')
        axes[1, 0].set_xlabel('客户等级')
        axes[1, 0].set_ylabel('隶属度')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)

        # 物料齐套率隶属函数
        axes[1, 1].plot(self.material_readiness.universe, self.material_readiness['低'].mf, 'r', label='低',
                        linewidth=2)
        axes[1, 1].plot(self.material_readiness.universe, self.material_readiness['中'].mf, 'g', label='中',
                        linewidth=2)
        axes[1, 1].plot(self.material_readiness.universe, self.material_readiness['高'].mf, 'b', label='高',
                        linewidth=2)
        axes[1, 1].set_title('物料齐套率隶属函数')
        axes[1, 1].set_xlabel('物料齐套率(%)')
        axes[1, 1].set_ylabel('隶属度')
        axes[1, 1].legend()
        axes[1, 1].grid(True, alpha=0.3)

        # 优先级隶属函数
        axes[2, 0].plot(self.priority.universe, self.priority['低'].mf, 'r', label='低', linewidth=2)
        axes[2, 0].plot(self.priority.universe, self.priority['中'].mf, 'g', label='中', linewidth=2)
        axes[2, 0].plot(self.priority.universe, self.priority['高'].mf, 'b', label='高', linewidth=2)
        axes[2, 0].set_title('优先级隶属函数')
        axes[2, 0].set_xlabel('优先级')
        axes[2, 0].set_ylabel('隶属度')
        axes[2, 0].legend()
        axes[2, 0].grid(True, alpha=0.3)

        # 移除多余的子图
        fig.delaxes(axes[2, 1])

        plt.tight_layout()
        plt.show()


class PriorityApp:
    """优先级计算系统的GUI界面"""

    def __init__(self, root):
        """初始化GUI应用"""
        self.root = root
        self.root.title("模糊逻辑优先级排序系统")
        self.root.geometry("800x600")

        # 初始化模糊系统
        self.fuzzy_system = FuzzyPrioritySystem()

        # 创建标签页
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建单订单计算标签页
        self.single_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.single_tab, text="单订单计算")

        # 创建批量计算标签页
        self.batch_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.batch_tab, text="批量计算")

        # 创建可视化标签页
        self.visual_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.visual_tab, text="可视化分析")

        # 初始化各标签页
        self._setup_single_tab()
        self._setup_batch_tab()
        self._setup_visual_tab()

    def _setup_single_tab(self):
        """设置单订单计算标签页"""
        # 创建输入框架
        input_frame = ttk.LabelFrame(self.single_tab, text="输入参数")
        input_frame.pack(fill=tk.X, padx=10, pady=10)

        # 订单金额
        ttk.Label(input_frame, text="订单金额 (0-10):").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.amount_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.amount_var, width=20).grid(row=0, column=1, padx=10, pady=5)

        # 剩余天数
        ttk.Label(input_frame, text="剩余天数 (0-100):").grid(row=1, column=0, padx=10, pady=5, sticky=tk.W)
        self.days_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.days_var, width=20).grid(row=1, column=1, padx=10, pady=5)

        # 客户等级
        ttk.Label(input_frame, text="客户等级 (1-5):").grid(row=2, column=0, padx=10, pady=5, sticky=tk.W)
        self.level_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.level_var, width=20).grid(row=2, column=1, padx=10, pady=5)

        # 物料齐套率
        ttk.Label(input_frame, text="物料齐套率 (0-100%):").grid(row=3, column=0, padx=10, pady=5, sticky=tk.W)
        self.readiness_var = tk.DoubleVar()
        ttk.Entry(input_frame, textvariable=self.readiness_var, width=20).grid(row=3, column=1, padx=10, pady=5)

        # 计算按钮
        ttk.Button(input_frame, text="计算优先级", command=self.calculate_single).grid(row=4, column=0, columnspan=2,
                                                                                       padx=10, pady=10)

        # 结果框架
        result_frame = ttk.LabelFrame(self.single_tab, text="计算结果")
        result_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Label(result_frame, text="优先级得分:").grid(row=0, column=0, padx=10, pady=5, sticky=tk.W)
        self.result_var = tk.StringVar()
        ttk.Label(result_frame, textvariable=self.result_var, font=('Arial', 12, 'bold')).grid(row=0, column=1, padx=10,
                                                                                               pady=5)

    def _setup_batch_tab(self):
        """设置批量计算标签页"""
        # 创建文件选择框架
        file_frame = ttk.LabelFrame(self.batch_tab, text="文件操作")
        file_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(file_frame, text="选择Excel文件", command=self.select_file).grid(row=0, column=0, padx=10, pady=5)
        self.file_var = tk.StringVar()
        ttk.Label(file_frame, textvariable=self.file_var, wraplength=600).grid(row=0, column=1, padx=10, pady=5,
                                                                               sticky=tk.W)

        # 计算按钮
        ttk.Button(file_frame, text="批量计算", command=self.calculate_batch).grid(row=1, column=0, columnspan=2,
                                                                                   padx=10, pady=10)

        # 结果框架
        result_frame = ttk.LabelFrame(self.batch_tab, text="计算结果")
        result_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # 创建表格
        columns = ('序号', '订单金额', '剩余天数', '客户等级', '物料齐套率', '优先级', '排名')
        self.tree = ttk.Treeview(result_frame, columns=columns, show='headings')

        # 设置列标题
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=100)

        # 添加滚动条
        scrollbar = ttk.Scrollbar(result_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscroll=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tree.pack(fill=tk.BOTH, expand=True)

    def _setup_visual_tab(self):
        """设置可视化分析标签页"""
        # 创建按钮框架
        button_frame = ttk.Frame(self.visual_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=10)

        ttk.Button(button_frame, text="绘制隶属函数", command=self.plot_membership).grid(row=0, column=0, padx=10,
                                                                                         pady=5)
        ttk.Button(button_frame, text="分析结果图表", command=self.plot_analysis).grid(row=0, column=1, padx=10, pady=5)

    def calculate_single(self):
        """计算单个订单的优先级"""
        try:
            # 获取输入值
            amount = self.amount_var.get()
            days = self.days_var.get()
            level = self.level_var.get()
            readiness = self.readiness_var.get()

            # 计算优先级
            priority = self.fuzzy_system.calculate_priority(amount, days, level, readiness)

            # 显示结果
            self.result_var.set(f"{priority:.2f}")

        except Exception as e:
            messagebox.showerror("错误", f"计算失败: {str(e)}")

    def select_file(self):
        """选择Excel文件"""
        file_path = filedialog.askopenfilename(
            title="选择Excel文件",
            filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*")]
        )
        if file_path:
            self.file_var.set(file_path)

    def calculate_batch(self):
        """批量计算订单优先级"""
        try:
            file_path = self.file_var.get()
            if not file_path:
                messagebox.showwarning("警告", "请先选择Excel文件")
                return

            # 读取Excel数据
            df = pd.read_excel(file_path, sheet_name='Sheet1')

            # 清理列名空格
            df.columns = df.columns.str.strip()

            # 重命名列以匹配内部逻辑
            df.rename(columns={
                '剩余天数 (天)': '剩余天数',
                '客户等级 (1-5)': '客户等级',
                '物料齐套率 (%)': '物料齐套率',
                '订单金额 (1-10)': '订单金额',
                '预期优先级 (0-100)': '预期优先级'
            }, inplace=True)

            # 数据预处理
            df['剩余天数'] = np.clip(df['剩余天数'], 0, 100)
            df['订单金额'] = np.clip(df['订单金额'], 0, 10)
            df['客户等级'] = np.clip(df['客户等级'], 1, 5)
            df['物料齐套率'] = np.clip(df['物料齐套率'], 0, 100)

            # 计算优先级
            priorities = self.fuzzy_system.calculate_batch_priority(df)
            df['算法优先级'] = priorities

            # 生成唯一排序
            tie_breaker_df = pd.DataFrame({
                'order_amount': df['订单金额'],
                'customer_level': df['客户等级'],
                'material_readiness': df['物料齐套率'],
                'remaining_days': -df['剩余天数']
            })

            df['算法排序'] = self.fuzzy_system.generate_unique_ranking(
                priorities,
                break_ties_with=tie_breaker_df
            )

            # 清空表格
            for item in self.tree.get_children():
                self.tree.delete(item)

            # 填充表格
            for idx, row in df.iterrows():
                self.tree.insert('', tk.END, values=(
                    idx + 1,
                    f"{row['订单金额']:.2f}",
                    f"{row['剩余天数']:.2f}",
                    f"{row['客户等级']:.2f}",
                    f"{row['物料齐套率']:.2f}",
                    f"{row['算法优先级']:.2f}",
                    row['算法排序']
                ))

            # 保存结果
            output_path = filedialog.asksaveasfilename(
                defaultextension=".xlsx",
                filetypes=[("Excel文件", "*.xlsx"), ("所有文件", "*")]
            )
            if output_path:
                df.to_excel(output_path, index=False)
                messagebox.showinfo("成功", f"结果已保存至: {output_path}")

        except Exception as e:
            messagebox.showerror("错误", f"批量计算失败: {str(e)}")

    def plot_membership(self):
        """绘制隶属函数"""
        try:
            self.fuzzy_system.plot_membership_functions()
        except Exception as e:
            messagebox.showerror("错误", f"绘制失败: {str(e)}")

    def plot_analysis(self):
        """绘制分析图表"""
        try:
            file_path = self.file_var.get()
            if not file_path:
                messagebox.showwarning("警告", "请先选择Excel文件")
                return

            # 读取Excel数据
            df = pd.read_excel(file_path, sheet_name='Sheet1')

            # 清理列名空格
            df.columns = df.columns.str.strip()

            # 重命名列以匹配内部逻辑
            df.rename(columns={
                '剩余天数 (天)': '剩余天数',
                '客户等级 (1-5)': '客户等级',
                '物料齐套率 (%)': '物料齐套率',
                '订单金额 (1-10)': '订单金额',
                '预期优先级 (0-100)': '预期优先级'
            }, inplace=True)

            # 数据预处理
            df['剩余天数'] = np.clip(df['剩余天数'], 0, 100)
            df['订单金额'] = np.clip(df['订单金额'], 0, 10)
            df['客户等级'] = np.clip(df['客户等级'], 1, 5)
            df['物料齐套率'] = np.clip(df['物料齐套率'], 0, 100)

            # 计算优先级
            priorities = self.fuzzy_system.calculate_batch_priority(df)
            df['算法优先级'] = priorities

            # 创建结果分析图表
            plt.figure(figsize=(15, 12))

            # 1. 优先级分布直方图
            plt.subplot(3, 2, 1)
            plt.hist(df['算法优先级'], bins=20, color='#4CAF50', edgecolor='black', alpha=0.7)
            plt.title('算法优先级分布')
            plt.xlabel('优先级得分')
            plt.ylabel('订单数量')
            plt.grid(True, alpha=0.3)

            # 2. 预期优先级 vs 算法优先级散点图
            plt.subplot(3, 2, 2)
            if '预期优先级' in df.columns and not df['预期优先级'].isna().all():
                plt.scatter(df['预期优先级'], df['算法优先级'], c='blue', alpha=0.6)
                plt.plot([0, 100], [0, 100], 'r--', linewidth=1)  # 对角线参考线
            plt.title('预期优先级 vs 算法优先级')
            plt.xlabel('预期优先级')
            plt.ylabel('算法优先级')
            plt.grid(True, alpha=0.3)

            # 3. 订单金额与优先级关系
            plt.subplot(3, 2, 3)
            plt.scatter(df['订单金额'], df['算法优先级'], c='orange', alpha=0.6)
            plt.title('订单金额 vs 算法优先级')
            plt.xlabel('订单金额')
            plt.ylabel('算法优先级')
            plt.grid(True, alpha=0.3)

            # 4. 剩余天数与优先级关系
            plt.subplot(3, 2, 4)
            plt.scatter(df['剩余天数'], df['算法优先级'], c='green', alpha=0.6)
            plt.title('剩余天数 vs 算法优先级')
            plt.xlabel('剩余天数')
            plt.ylabel('算法优先级')
            plt.grid(True, alpha=0.3)

            # 5. 客户等级与优先级关系
            plt.subplot(3, 2, 5)
            customer_levels = sorted(df['客户等级'].unique())
            box_data = [df[df['客户等级'] == level]['算法优先级'] for level in customer_levels]
            plt.boxplot(box_data, tick_labels=[f'等级{level}' for level in customer_levels])
            plt.title('客户等级 vs 算法优先级')
            plt.xlabel('客户等级')
            plt.ylabel('算法优先级')
            plt.grid(True, alpha=0.3)

            # 6. 物料齐套率与优先级关系
            plt.subplot(3, 2, 6)
            plt.scatter(df['物料齐套率'], df['算法优先级'], c='purple', alpha=0.6)
            plt.title('物料齐套率 vs 算法优先级')
            plt.xlabel('物料齐套率(%)')
            plt.ylabel('算法优先级')
            plt.grid(True, alpha=0.3)

            plt.tight_layout()
            plt.show()

        except Exception as e:
            messagebox.showerror("错误", f"绘制失败: {str(e)}")


def main():
    """主函数：处理Excel数据并生成排序（包含物料齐套率）"""
    # 读取Excel数据
    try:
        df = pd.read_excel('D:\\da.xlsx', sheet_name='Sheet1')
    except Exception as e:
        print(f"读取Excel文件失败: {str(e)}")
        return

    # 清理列名空格
    df.columns = df.columns.str.strip()

    # 定义预期列
    expected_columns = ['剩余天数 (天)', '客户等级 (1-5)', '物料齐套率 (%)', '订单金额 (1-10)', '预期优先级 (0-100)']

    # 检查列是否存在
    for col in expected_columns:
        if col not in df.columns:
            print(f"警告: Excel中缺少列 '{col}'")

    # 重命名列以匹配内部逻辑
    df.rename(columns={
        '剩余天数 (天)': '剩余天数',
        '客户等级 (1-5)': '客户等级',
        '物料齐套率 (%)': '物料齐套率',
        '订单金额 (1-10)': '订单金额',
        '预期优先级 (0-100)': '预期优先级'
    }, inplace=True)

    # 数据预处理
    df['剩余天数'] = np.clip(df['剩余天数'], 0, 100)  # 剩余天数范围 0-100
    df['订单金额'] = np.clip(df['订单金额'], 0, 10)  # 订单金额范围 0-10
    df['客户等级'] = np.clip(df['客户等级'], 1, 5)  # 客户等级范围 1-5
    df['物料齐套率'] = np.clip(df['物料齐套率'], 0, 100)  # 物料齐套率范围 0-100

    # 初始化模糊系统
    fuzzy_system = FuzzyPrioritySystem()

    # 计算批量优先级（包含物料齐套率）
    print("开始计算订单优先级（包含物料齐套率）...")
    priorities = fuzzy_system.calculate_batch_priority(df)

    # 添加优先级列到DataFrame
    df['算法优先级'] = priorities

    # 生成唯一排序（使用辅助列打破平局，确保排序从1到n不重复）
    print("生成唯一排序...")

    # 准备用于打破平局的辅助数据
    # 优先级相同时，按订单金额降序、客户等级降序、物料齐套率降序、剩余天数升序排序
    tie_breaker_df = pd.DataFrame({
        'order_amount': df['订单金额'],
        'customer_level': df['客户等级'],
        'material_readiness': df['物料齐套率'],  # 新增物料齐套率
        'remaining_days': -df['剩余天数']  # 剩余天数升序（负数实现降序效果）
    })

    # 生成唯一排名
    df['算法排序'] = fuzzy_system.generate_unique_ranking(
        priorities,
        break_ties_with=tie_breaker_df
    )

    # 验证排序的唯一性
    unique_ranks = df['算法排序'].unique()
    print(f"生成唯一排名: 1-{len(df)}")
    print(f"实际排名数量: {len(unique_ranks)}")
    print(f"排名是否唯一: {len(unique_ranks) == len(df)}")
    print(f"排名范围: {df['算法排序'].min()}-{df['算法排序'].max()}")

    # 保存结果到Excel
    output_path = 'D:\\result_with_material_readiness.xlsx'
    df.to_excel(output_path, index=False)
    print(f"✅ 已完成优先级计算（含物料齐套率）和唯一排序，结果保存至 {output_path}")

    # 显示结果摘要
    print("\n结果摘要:")
    print(f"总订单数: {len(df)}")
    print(f"平均优先级: {df['算法优先级'].mean():.2f}")
    print(f"最高优先级: {df['算法优先级'].max():.2f}")
    print(f"最低优先级: {df['算法优先级'].min():.2f}")
    print(f"平均物料齐套率: {df['物料齐套率'].mean():.2f}%")

    # 显示前10个订单的排序结果
    print("\n前10个订单的排序结果:")
    print("-" * 85)
    print(
        f"{'序号':<5} {'订单金额':<10} {'剩余天数':<10} {'客户等级':<10} {'物料齐套率':<12} {'优先级':<10} {'排名':<5}")
    print("-" * 85)
    for idx, row in df.head(10).iterrows():
        print(f"{idx + 1:<5} {row['订单金额']:<10.2f} {row['剩余天数']:<10.2f} "
              f"{row['客户等级']:<10.2f} {row['物料齐套率']:<12.2f} {row['算法优先级']:<10.2f} {row['算法排序']:<5}")
    print("-" * 85)

    # 检查是否存在"预期优先级"列用于评估
    if '预期优先级' in df.columns and not df['预期优先级'].isna().all():
        # 计算相关性
        correlation = df['算法优先级'].corr(df['预期优先级'])
        print(f"\n评估指标:")
        print(f"算法优先级与预期优先级的相关性: {correlation:.4f}")

        # 计算排序准确率（排名完全一致的比例）
        if '预期排序' not in df.columns:
            # 如果预期优先级有值，生成预期排序（同样需要唯一排名）
            # 使用相同的方法生成唯一预期排序
            expected_tie_breaker_df = pd.DataFrame({
                'order_amount': df['订单金额'],
                'customer_level': df['客户等级'],
                'material_readiness': df['物料齐套率'],  # 新增物料齐套率
                'remaining_days': -df['剩余天数']
            })
            df['预期排序'] = fuzzy_system.generate_unique_ranking(
                df['预期优先级'].fillna(0).values,
                break_ties_with=expected_tie_breaker_df
            )

        # 计算排名差异
        rank_diff = df['算法排序'] - df['预期排序']
        mean_abs_diff = np.abs(rank_diff).mean()

        print(f"平均绝对排名差异: {mean_abs_diff:.2f}")
        print(f"最大排名差异: {np.abs(rank_diff).max()}")

    # 可视化
    print("\n生成可视化图表...")

    # 创建结果分析图表
    plt.figure(figsize=(15, 12))

    # 1. 优先级分布直方图
    plt.subplot(3, 2, 1)
    plt.hist(df['算法优先级'], bins=20, color='#4CAF50', edgecolor='black', alpha=0.7)
    plt.title('算法优先级分布')
    plt.xlabel('优先级得分')
    plt.ylabel('订单数量')
    plt.grid(True, alpha=0.3)

    # 2. 预期优先级 vs 算法优先级散点图
    plt.subplot(3, 2, 2)
    if '预期优先级' in df.columns and not df['预期优先级'].isna().all():
        plt.scatter(df['预期优先级'], df['算法优先级'], c='blue', alpha=0.6)
        plt.plot([0, 100], [0, 100], 'r--', linewidth=1)  # 对角线参考线
    plt.title('预期优先级 vs 算法优先级')
    plt.xlabel('预期优先级')
    plt.ylabel('算法优先级')
    plt.grid(True, alpha=0.3)

    # 3. 订单金额与优先级关系
    plt.subplot(3, 2, 3)
    plt.scatter(df['订单金额'], df['算法优先级'], c='orange', alpha=0.6)
    plt.title('订单金额 vs 算法优先级')
    plt.xlabel('订单金额')
    plt.ylabel('算法优先级')
    plt.grid(True, alpha=0.3)

    # 4. 剩余天数与优先级关系
    plt.subplot(3, 2, 4)
    plt.scatter(df['剩余天数'], df['算法优先级'], c='green', alpha=0.6)
    plt.title('剩余天数 vs 算法优先级')
    plt.xlabel('剩余天数')
    plt.ylabel('算法优先级')
    plt.grid(True, alpha=0.3)

    # 5. 客户等级与优先级关系
    plt.subplot(3, 2, 5)
    customer_levels = sorted(df['客户等级'].unique())
    box_data = [df[df['客户等级'] == level]['算法优先级'] for level in customer_levels]
    plt.boxplot(box_data, tick_labels=[f'等级{level}' for level in customer_levels])
    plt.title('客户等级 vs 算法优先级')
    plt.xlabel('客户等级')
    plt.ylabel('算法优先级')
    plt.grid(True, alpha=0.3)

    # 6. 物料齐套率与优先级关系
    plt.subplot(3, 2, 6)
    plt.scatter(df['物料齐套率'], df['算法优先级'], c='purple', alpha=0.6)
    plt.title('物料齐套率 vs 算法优先级')
    plt.xlabel('物料齐套率(%)')
    plt.ylabel('算法优先级')
    plt.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig('D:\\priority_analysis_with_material.png', dpi=300, bbox_inches='tight')
    plt.show()

    print("✅ 分析完成！")


# 测试用例（更新为包含物料齐套率）
def test_fuzzy_system():
    """测试模糊逻辑系统（包含物料齐套率）"""
    print("测试模糊逻辑系统（包含物料齐套率）...")

    # 创建测试系统
    fuzzy_system = FuzzyPrioritySystem()

    # 测试用例（包含物料齐套率）
    test_cases = [
        (9.5, 5, 5, 95, "高优先级：金额高、客户等级高、剩余天数少、物料齐套率高"),
        (8.0, 20, 4, 90, "高优先级：金额高、客户等级中高、剩余天数中等、物料齐套率高"),
        (5.0, 50, 3, 50, "中优先级：金额中等、客户等级中等、剩余天数中等、物料齐套率中等"),
        (2.0, 80, 2, 30, "低优先级：金额低、客户等级低、剩余天数多、物料齐套率低"),
        (1.0, 95, 1, 10, "最低优先级：金额很低、客户等级很低、剩余天数很多、物料齐套率很低"),
        (7.0, 10, 4, 20, "中优先级：金额高、客户等级高、剩余天数少但物料齐套率低"),
        (4.0, 60, 3, 80, "中高优先级：金额中等、客户等级中等、剩余天数中等、物料齐套率高"),
    ]

    print("\n测试用例结果:")
    print("-" * 75)
    print(f"{'订单金额':<8} {'剩余天数':<8} {'客户等级':<8} {'物料齐套率':<10} {'优先级':<8} {'描述':<30}")
    print("-" * 75)

    for amount, days, level, readiness, description in test_cases:
        priority = fuzzy_system.calculate_priority(amount, days, level, readiness)
        print(f"{amount:<8.1f} {days:<8.1f} {level:<8.1f} {readiness:<10.1f} {priority:<8.2f} {description:<30}")

    print("-" * 75)


if __name__ == "__main__":
    # 检查是否需要启动GUI
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "--gui":
        # 启动GUI模式
        root = tk.Tk()
        app = PriorityApp(root)
        root.mainloop()
    else:
        # 运行测试
        test_fuzzy_system()

        print("\n" + "=" * 60)
        print("开始主程序执行...")
        print("=" * 60)

        # 运行主程序
        main()