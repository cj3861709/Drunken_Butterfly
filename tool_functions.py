"""
绘图工具函数

基于 Plotly Express 实现统一的图表绘制接口。
支持15+种可视化图表类型，所有图表均返回 Plotly Figure 对象，
可在 Streamlit 中通过 st.plotly_chart 直接渲染。
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sqlalchemy import create_engine, text
import os
import glob


# 支持的 Excel 扩展名（pd.read_excel 原生支持）
EXCEL_EXTENSIONS = {".xlsx", ".xls", ".xlsm", ".xlsb", ".xltx", ".xltm"}
# 支持的 CSV 扩展名
CSV_EXTENSIONS = {".csv"}


def read_file(file_path: str, sheet_name: int = 0) -> pd.DataFrame:
    """
    自动识别文件类型并读取。

    支持以下格式：
    - Excel: .xlsx, .xls, .xlsm, .xlsb, .xltx, .xltm
    - CSV:   .csv

    Args:
        file_path: 文件路径
        sheet_name: Excel 工作表索引（从 0 开始），仅 Excel 文件有效

    Returns:
        pd.DataFrame
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"文件不存在: {file_path}")

    ext = os.path.splitext(file_path)[1].lower()

    if ext in EXCEL_EXTENSIONS:
        return pd.read_excel(file_path, sheet_name=sheet_name)
    elif ext in CSV_EXTENSIONS:
        return pd.read_csv(file_path)
    else:
        fmt_list = ", ".join(sorted(EXCEL_EXTENSIONS | CSV_EXTENSIONS))
        raise ValueError(
            f"不支持的文件格式: {ext}\n"
            f"支持的格式: {fmt_list}"
        )


def query_mysql(connection_string: str, sql: str) -> pd.DataFrame:
    """执行 MySQL 查询并返回 DataFrame"""
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        return pd.read_sql(text(sql), conn)


def create_chart(
    df: pd.DataFrame,
    chart_type: str,
    x_col: str,
    y_col: str = None,
    color_col: str = None,
    z_col: str = None,
    title: str = "图表"
) -> go.Figure:
    """
    通用图表绘制函数，支持15+种图表类型。

    Args:
        df: 数据 DataFrame
        chart_type: 图表类型
        x_col: X 轴列名
        y_col: Y 轴列名（可选）
        color_col: 颜色分组列名（可选）
        z_col: Z 值列名（可选，仅 heatmap）
        title: 图表标题

    Returns:
        plotly.graph_objects.Figure
    """
    chart_type = chart_type.lower().replace("-", "_")

    # ========== 基础类型 ==========
    if chart_type == "line":
        fig = px.line(df, x=x_col, y=y_col, title=title)

    elif chart_type == "bar":
        fig = px.bar(df, x=x_col, y=y_col, title=title)

    elif chart_type == "scatter":
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title)

    elif chart_type == "pie":
        # 饼图：x_col=分类, y_col=数值
        fig = px.pie(df, names=x_col, values=y_col, title=title)

    elif chart_type == "histogram":
        # 直方图：只需 x_col
        fig = px.histogram(df, x=x_col, color=color_col, title=title)

    elif chart_type == "box":
        fig = px.box(df, x=x_col, y=y_col, color=color_col, title=title)

    elif chart_type == "violin":
        fig = px.violin(df, x=x_col, y=y_col, color=color_col, title=title)

    elif chart_type == "area":
        fig = px.area(df, x=x_col, y=y_col, color=color_col, title=title)

    # ========== 热力图 ==========
    elif chart_type == "heatmap":
        if y_col and z_col:
            # 透视表格式：x_col/y_col 作为行列，z_col 作为值
            pivot_df = df.pivot_table(
                index=y_col, columns=x_col, values=z_col, aggfunc="mean"
            )
            fig = px.imshow(pivot_df, title=title, aspect="auto")
        else:
            # 直接传入矩阵数据
            fig = px.imshow(
                df.select_dtypes("number").values,
                title=title,
                aspect="auto",
                labels={"x": x_col, "y": y_col or "index"}
            )

    elif chart_type == "density_heatmap":
        fig = px.density_heatmap(
            df, x=x_col, y=y_col or x_col,
            title=title
        )

    # ========== 层级/树形图 ==========
    elif chart_type == "sunburst":
        # 旭日图：x_col 为路径列（用 / 分隔的层级），y_col 为数值
        fig = px.sunburst(
            df, path=[x_col] if "/" not in x_col else x_col.split("/"),
            values=y_col, title=title
        )

    elif chart_type == "treemap":
        fig = px.treemap(
            df, path=[x_col] if "/" not in x_col else x_col.split("/"),
            values=y_col, title=title
        )

    elif chart_type == "funnel":
        fig = px.funnel(df, x=x_col, y=y_col, title=title)

    # ========== 变体类型 ==========
    elif chart_type == "bar_horizontal":
        fig = px.bar(df, x=x_col, y=y_col, orientation="h", title=title)

    elif chart_type == "line_group":
        # 多组折线图（用 color_col 区分组）
        fig = px.line(df, x=x_col, y=y_col, color=color_col, title=title)

    elif chart_type == "scatter_group":
        fig = px.scatter(df, x=x_col, y=y_col, color=color_col, title=title)

    elif chart_type == "bar_stacked":
        # 堆叠柱状图
        fig = px.bar(df, x=x_col, y=y_col, color=color_col, title=title, barmode="stack")

    else:
        # 默认回退为柱状图
        fig = px.bar(df, x=x_col, y=y_col, title=f"{title} (默认: bar)")

    # 统一优化布局
    fig.update_layout(
        title_font_size=16,
        xaxis_title_font_size=13,
        yaxis_title_font_size=13,
        legend_title_font_size=12,
        margin=dict(l=40, r=40, t=60, b=40),
        hovermode="x unified" if chart_type in ("line", "area", "line_group") else "closest"
    )

    return fig


def _is_excel_file(filename: str) -> bool:
    """判断文件名是否为支持的 Excel 格式"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in EXCEL_EXTENSIONS


def _is_csv_file(filename: str) -> bool:
    """判断文件名是否为 CSV 格式"""
    ext = os.path.splitext(filename)[1].lower()
    return ext in CSV_EXTENSIONS


def list_data_files(folder_path: str) -> list:
    """
    扫描指定文件夹下的所有数据文件。

    支持以下格式：
    - Excel: .xlsx, .xls, .xlsm, .xlsb, .xltx, .xltm
    - CSV:   .csv

    返回按修改时间降序排列的绝对路径列表。
    """
    if not os.path.exists(folder_path):
        return []

    files = []
    # 匹配所有支持的 Excel 扩展名
    for ext in EXCEL_EXTENSIONS:
        files.extend(glob.glob(os.path.join(folder_path, f"*{ext}")))
        # 也匹配大写版本（某些系统不区分大小写，但 glob 可能区分）
        files.extend(glob.glob(os.path.join(folder_path, f"*{ext.upper()}")))
    # 匹配 CSV
    files.extend(glob.glob(os.path.join(folder_path, "*.csv")))
    files.extend(glob.glob(os.path.join(folder_path, "*.CSV")))

    # 去重 + 按修改时间排序，最新的在前面
    files = sorted(set(files), key=os.path.getmtime, reverse=True)
    return files