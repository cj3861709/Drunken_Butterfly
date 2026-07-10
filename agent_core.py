"""
Agent 核心逻辑

基于 OpenAI Function Calling 实现智能数据分析 Agent。
支持以下工具调用：
- read_file: 读取数据文件（Excel / CSV）
- query_mysql: 查询 MySQL 数据库
- get_data_full: 获取内存中数据源的完整数据（可按列筛选）
- create_chart: 通用图表绘制（折线图、柱状图、散点图、饼图、箱线图等15+种）
"""

import json
import pandas as pd
from openai import OpenAI
from config import DEEPSEEK_API_KEY, DEEPSEEK_BASE_URL, MYSQL_CONNECTION_STRING
from tool_functions import read_file, query_mysql, create_chart
from analysis_script import (
    data_profile,
    correlation_analysis,
    statistical_summary,
    detect_outliers,
    distribution_analysis,
    group_analysis,
)

# 初始化 OpenAI 客户端（兼容 DeepSeek API）
client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL,
)

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取数据文件（Excel 或 CSV）并返回数据摘要（行数、列名、前5行）",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "文件路径（支持 .xlsx、.xls、.csv）"
                    },
                    "sheet_name": {
                        "type": "integer",
                        "description": "Excel 工作表索引，从0开始（仅 .xlsx/.xls 有效）",
                        "default": 0
                    }
                },
                "required": ["file_path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "query_mysql",
            "description": "执行 MySQL 查询。结果会自动存入内存数据源（名称如 mysql_表名），后续可直接用 run_analysis(source_name='mysql_表名') 进行深度分析，无需再次传数据",
            "parameters": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL 查询语句"
                    }
                },
                "required": ["sql"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_data_full",
            "description": "从内存中获取某个数据源的完整数据（JSON格式）。数据源名称由上下文中的【数据表: 名称】指定。对于大数据表，建议使用columns参数筛选需要的列以减少token消耗。",
            "parameters": {
                "type": "object",
                "properties": {
                    "source_name": {
                        "type": "string",
                        "description": "数据源的名称（即上下文中【数据表: xxx】里的 xxx）"
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "需要返回的列名列表（可选）。不传则返回所有列。建议只传需要的列以减少token。"
                    }
                },
                "required": ["source_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "run_analysis",
            "description": "对数据源进行深度统计分析。支持：data_profile(数据概览)、correlation_analysis(相关性分析)、statistical_summary(详细统计摘要)、detect_outliers(异常值检测)、distribution_analysis(分布分析)、group_analysis(分组聚合)。使用方式：传入 source_name 指定数据源（推荐，无需先调get_data_full），或传入 data_json 传入完整数据。",
            "parameters": {
                "type": "object",
                "properties": {
                    "analysis_type": {
                        "type": "string",
                        "enum": [
                            "data_profile",
                            "correlation_analysis",
                            "statistical_summary",
                            "detect_outliers",
                            "distribution_analysis",
                            "group_analysis"
                        ],
                        "description": "分析类型：data_profile(数据概览:缺失值/类型/分布)、correlation_analysis(相关性分析)、statistical_summary(详细统计摘要:分位数/偏度/峰度等)、detect_outliers(异常值检测:IQR/Z-Score)、distribution_analysis(分布分析:分箱/频数)、group_analysis(分组聚合:mean/sum/count等)"
                    },
                    "source_name": {
                        "type": "string",
                        "description": "数据源名称（即【数据表: 名称】里的名称）。提供此参数时会自动从内存中读取数据，无需先调 get_data_full。"
                    },
                    "data_json": {
                        "type": "string",
                        "description": "数据的 JSON 字符串（如果是从 get_data_full 获取的完整数据，可传入此参数）。与 source_name 二选一。"
                    },
                    "column": {
                        "type": "string",
                        "description": "分析的目标列名（仅 detect_outliers 和 distribution_analysis 需要）"
                    },
                    "group_col": {
                        "type": "string",
                        "description": "分组列名（仅 group_analysis 需要）"
                    },
                    "value_col": {
                        "type": "string",
                        "description": "数值列名（仅 group_analysis 需要）"
                    },
                    "agg_func": {
                        "type": "string",
                        "enum": ["mean", "sum", "count", "max", "min", "std", "median"],
                        "description": "聚合函数（仅 group_analysis 需要，默认 mean）"
                    },
                    "method": {
                        "type": "string",
                        "enum": ["pearson", "spearman", "kendall", "iqr", "zscore"],
                        "description": "相关方法（correlation_analysis: pearson/spearman/kendall）或异常检测方法（detect_outliers: iqr/zscore）"
                    },
                    "columns": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "需要统计的列名列表（仅 statistical_summary 需要，不传则分析所有数值列）"
                    },
                    "bins": {
                        "type": "integer",
                        "description": "分箱数（仅 distribution_analysis 需要，默认10）"
                    },
                    "threshold": {
                        "type": "number",
                        "description": "异常检测阈值（仅 detect_outliers 需要，IQR默认1.5，Z-Score默认3）"
                    }
                },
                "required": ["analysis_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "create_chart",
            "description": "根据数据绘制各种类型的可视化图表，支持15+种图表类型",
            "parameters": {
                "type": "object",
                "properties": {
                    "chart_type": {
                        "type": "string",
                        "enum": [
                            "line", "bar", "scatter", "pie", "histogram",
                            "box", "violin", "area", "heatmap", "density_heatmap",
                            "sunburst", "treemap", "funnel", "bar_horizontal",
                            "line_group", "scatter_group", "bar_stacked"
                        ],
                        "description": "图表类型：line/bar/scatter/pie/histogram/box/violin/area/heatmap/density_heatmap/sunburst/treemap/funnel/bar_horizontal/line_group/scatter_group/bar_stacked"
                    },
                    "data_json": {
                        "type": "string",
                        "description": "数据的 JSON 字符串（包含所有需要的列）。先用 get_data_full 获取完整数据或所需列，提取后传入此参数。"
                    },
                    "x_col": {
                        "type": "string",
                        "description": "X 轴列名（饼图/直方图/旭日图等作为主分类列）"
                    },
                    "y_col": {
                        "type": "string",
                        "description": "Y 轴列名（数值列），部分图表可留空"
                    },
                    "color_col": {
                        "type": "string",
                        "description": "颜色分组列名（可选，用于 group/stacked 类型图表）"
                    },
                    "z_col": {
                        "type": "string",
                        "description": "Z 值列名（可选，仅 heatmap 等需要）"
                    },
                    "title": {
                        "type": "string",
                        "description": "图表标题（可选）"
                    }
                },
                "required": ["chart_type", "data_json", "x_col"]
            }
        }
    }
]


def _get_data_summary(df: pd.DataFrame, name: str, max_head: int = 3) -> str:
    """构建紧凑的数据源摘要（不嵌入原始数据，只告诉 LLM 结构和统计特征）"""
    rows, cols = len(df), len(df.columns)
    col_names = list(df.columns)
    dtypes = {c: str(df[c].dtype) for c in col_names}

    # 紧凑列信息：列名(类型)
    col_info = ", ".join(f"{c}({dtypes[c]})" for c in col_names[:12])
    if len(col_names) > 12:
        col_info += f" ... 共{cols}列"

    # 数值列统计（用Series方法直接算，效率高）
    num_cols = df.select_dtypes(include="number").columns[:5]
    stats_lines = []
    for c in num_cols:
        s = df[c].dropna()
        if len(s) > 0:
            stats_lines.append(f"    {c}: min={s.min():.2f}, max={s.max():.2f}, mean={s.mean():.2f}")
    stats_str = "\n".join(stats_lines)

    # 前几行预览（紧凑格式，一行JSON）
    preview = df.head(max_head).to_json(orient="records", force_ascii=False)

    parts = [
        f"【数据表: {name}】",
        f"  - 行数: {rows}, 列数: {cols}",
        f"  - 列: {col_info}",
        f"  - 前{max_head}行: {preview[:600]}{'...' if len(preview) > 600 else ''}",
    ]
    if stats_str:
        parts.append(f"  - 数值列统计:\n{stats_str}")
    if rows > 500:
        parts.append(f"  - ⚠️ 数据量较大({rows}行)，如需分析请用 get_data_full(columns=[需要的列]) 获取指定列的数据")

    return "\n".join(parts)


def ask_question(question: str, file_path: str = None, data_sources: dict = None):
    """
    向 Agent 提问

    Args:
        question: 用户的问题
        file_path: 当前选中的 Excel 文件路径（可选）
        data_sources: 所有数据源字典 {name: {type, df, content, path, ...}}

    Returns:
        tuple: (text_answer, list_of_plotly_figures)
    """
    # ---------- 构建数据源上下文（紧凑格式） ----------
    context_parts = []
    if data_sources:
        for name, ds in data_sources.items():
            if ds.get("df") is not None:
                context_parts.append(_get_data_summary(ds["df"], name))
            elif ds.get("content"):
                c = ds["content"]
                context_parts.append(
                    f"【文档: {name}】\n  - 长度: {len(c)}字\n  - 前500字: {c[:500]}"
                )

    if file_path:
        context_parts.append(f"【当前绑定文件】\n{file_path}")

    # ---------- System Prompt ----------
    system_content = (
        "你是一位专业的数据分析专家助手。当前已加载了多个数据源到内存中。\n\n"
        "工作流程：\n"
        "1. 上方列出了所有数据源的摘要（行数、列名、类型、前几行预览、数值列统计）\n"
        "2. 对于大数据表（摘要中有⚠️标记），必须先用 get_data_full 获取完整数据：\n"
        "   - 建议用 columns 参数只选取需要的列，避免token超限\n"
        "3. 获取到完整数据后，提取所需列构建 JSON 数组，调用 create_chart 绘图\n"
        "4. 使用 query_mysql 查询 MySQL 后，结果会自动存入内存数据源（数据源名称如 mysql_表名），"
        "   可直接用 run_analysis(source_name='mysql_表名') 进行深度分析，无需再次传数据\n"
        "5. 对于深度统计分析，使用 run_analysis 工具（推荐）：\n"
        "   - 直接传入 source_name 参数指定数据源名称（如【数据表: 销售数据】中'销售数据'），无需先调 get_data_full\n"
        "   - 如果只有单个数据源，甚至可以只传 analysis_type，run_analysis会自动读取\n"
        "   - data_profile: 数据完整画像（缺失值、类型、分布、唯一值等）\n"
        "   - correlation_analysis: 数值列相关性分析（pearson/spearman/kendall）\n"
        "   - statistical_summary: 详细统计摘要（分位数、偏度、峰度、变异系数等）\n"
        "   - detect_outliers: 异常值检测（IQR/Z-Score方法）\n"
        "   - distribution_analysis: 分布分析（分箱频数统计）\n"
        "   - group_analysis: 分组聚合分析（mean/sum/count/max/min/std/median）\n\n"
        "图表类型：line(折线), bar(柱状), scatter(散点), pie(饼图), histogram(直方图),\n"
        "box(箱线), violin(小提琴), area(面积), heatmap(热力), sunburst(旭日),\n"
        "treemap(矩形树), funnel(漏斗), bar_horizontal(水平柱状),\n"
        "line_group(多组折线), scatter_group(多组散点), bar_stacked(堆叠柱状)\n\n"
        "所有分析结果请用中文回答。图表工具调用成功后只需做文字说明。"
    )
    messages = [{"role": "system", "content": system_content}]

    # ---------- 组装用户消息 ----------
    if context_parts:
        context_msg = "## 当前可用数据源\n\n" + "\n\n".join(context_parts)
        context_msg += f"\n\n## 用户需求\n{question}"
        messages.append({"role": "user", "content": context_msg})
    else:
        messages.append({"role": "user", "content": question})

    # ---------- 多轮对话循环 ----------
    max_turns = 15
    turn_count = 0
    figures = []

    while turn_count < max_turns:
        turn_count += 1

        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )

        choice = response.choices[0]
        message = choice.message

        if not message.tool_calls:
            return message.content or "分析完成。", figures

        # 记录 assistant 消息
        assistant_msg = {"role": "assistant", "content": message.content}
        if message.tool_calls:
            assistant_msg["tool_calls"] = []
            for tc in message.tool_calls:
                assistant_msg["tool_calls"].append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                })
        messages.append(assistant_msg)

        # 执行工具调用
        for tool_call in message.tool_calls:
            func_name = tool_call.function.name
            try:
                func_args = json.loads(tool_call.function.arguments)
            except json.JSONDecodeError:
                func_args = {}

            result_str = ""
            try:
                if func_name == "read_file":
                    df = read_file(**func_args)
                    summary = {
                        "行数": len(df),
                        "列数": len(df.columns),
                        "列名": list(df.columns),
                        "数据类型": {col: str(dtype) for col, dtype in df.dtypes.items()},
                        "前5行数据": df.head(5).to_dict(orient="records"),
                    }
                    result_str = json.dumps(summary, ensure_ascii=False, default=str)

                elif func_name == "query_mysql":
                    if not MYSQL_CONNECTION_STRING:
                        result_str = "错误：未配置 MySQL 连接，请在 .env 中设置 MYSQL_CONNECTION_STRING"
                    else:
                        sql = func_args.get("sql", "")
                        df = query_mysql(MYSQL_CONNECTION_STRING, sql)
                        # 从 SQL 提取表名作为数据源名称
                        import re
                        table_match = re.search(r"(?:from|FROM|join|JOIN)\s+`?(\w+)`?", sql)
                        src_name = f"mysql_{table_match.group(1)}" if table_match else f"mysql_query_{len(data_sources) + 1}"
                        # 存入 data_sources（后续可直接用 run_analysis(source_name=...) 分析）
                        if data_sources is not None:
                            data_sources[src_name] = {
                                "type": "dataframe",
                                "df": df,
                                "content": None,
                                "path": None,
                                "rows": len(df),
                                "cols": list(df.columns),
                            }
                        result_str = json.dumps({
                            "行数": len(df),
                            "列名": list(df.columns),
                            "数据类型": {col: str(dtype) for col, dtype in df.dtypes.items()},
                            "数据源名称": src_name,
                            "列统计摘要": _get_data_summary(df, src_name),
                            "提示": f"MySQL 数据已存入内存数据源「{src_name}」。上方「列统计摘要」已包含完整的列信息和数值统计，可直接据此得出结论或调用 create_chart 绘制图表。如需更深度分析，可用 run_analysis(source_name='{src_name}')。",
                            "数据预览": df.head(10).to_dict(orient="records")
                        }, ensure_ascii=False, default=str)

                elif func_name == "get_data_full":
                    source_name = func_args.get("source_name", "")
                    columns = func_args.get("columns", None)  # 可选：筛选列
                    max_rows = 300  # 最多返回300行，减少token消耗
                    if data_sources and source_name in data_sources:
                        ds = data_sources[source_name]
                        if ds.get("df") is not None:
                            df_full = ds["df"]
                            if columns:
                                # 只保留请求的列
                                valid_cols = [c for c in columns if c in df_full.columns]
                                if valid_cols:
                                    df_full = df_full[valid_cols]
                                else:
                                    result_str = f"指定的列 {columns} 都不存在于数据表中，可用列: {list(df_full.columns)}"
                                    messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_str})
                                    continue
                            total_rows = len(df_full)
                            if total_rows > max_rows:
                                result_str = json.dumps({
                                    "警告": f"数据共 {total_rows} 行，仅返回前 {max_rows} 行。如需完整数据请使用columns参数筛选更少的列后重试",
                                    "行数": total_rows,
                                    "返回行数": max_rows,
                                    "列名": list(df_full.columns),
                                    "数据": df_full.head(max_rows).to_dict(orient="records")
                                }, ensure_ascii=False, default=str)
                            else:
                                result_str = json.dumps({
                                    "行数": total_rows,
                                    "列名": list(df_full.columns),
                                    "数据": df_full.to_dict(orient="records")
                                }, ensure_ascii=False, default=str)
                        else:
                            result_str = f"数据源 {source_name} 没有 DataFrame 数据"
                    else:
                        result_str = f"数据源 {source_name} 不存在。可用的数据源有: {list(data_sources.keys()) if data_sources else '无'}"

                elif func_name == "run_analysis":
                    analysis_type = func_args.get("analysis_type", "data_profile")
                    source_name = func_args.get("source_name", None)
                    data_json = func_args.get("data_json", None)
                    column = func_args.get("column", None)
                    group_col = func_args.get("group_col", None)
                    value_col = func_args.get("value_col", None)
                    agg_func = func_args.get("agg_func", "mean")
                    method = func_args.get("method", None)
                    columns = func_args.get("columns", None)
                    bins = func_args.get("bins", 10)
                    threshold = func_args.get("threshold", None)

                    # 支持通过 source_name 自动获取数据（省去 get_data_full 步骤）
                    # 直接传 DataFrame 对象，避免 JSON 序列化/反序列化开销
                    if source_name and data_sources and source_name in data_sources:
                        ds = data_sources[source_name]
                        if ds.get("df") is not None:
                            df = ds["df"]
                            # 直接传 DataFrame 而非 JSON 字符串，由 analysis_script 内部处理
                            data_json = df
                        else:
                            result_str = f"数据源 {source_name} 没有 DataFrame 数据"
                            messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_str})
                            continue
                    elif isinstance(data_json, str) and (not data_json or data_json == "[]"):
                        # 尝试从当前唯一数据源自动获取
                        if data_sources and len(data_sources) == 1:
                            only_name = list(data_sources.keys())[0]
                            ds = data_sources[only_name]
                            if ds.get("df") is not None:
                                data_json = ds["df"]  # 直接传 DataFrame

                    if isinstance(data_json, str) and (not data_json or data_json == "[]"):
                        result_str = "错误：请提供 source_name 或 data_json 参数。可用的数据源: " + ", ".join(data_sources.keys()) if data_sources else "无"
                        messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result_str})
                        continue

                    try:
                        if analysis_type == "data_profile":
                            result_str = data_profile(data_json)
                        elif analysis_type == "correlation_analysis":
                            m = method or "pearson"
                            result_str = correlation_analysis(data_json, method=m)
                        elif analysis_type == "statistical_summary":
                            result_str = statistical_summary(data_json, columns=columns)
                        elif analysis_type == "detect_outliers":
                            if not column:
                                result_str = json.dumps({"错误": "detect_outliers 需要指定 column 参数"}, ensure_ascii=False)
                            else:
                                m = method or "iqr"
                                t = threshold or 1.5
                                result_str = detect_outliers(data_json, column=column, method=m, threshold=t)
                        elif analysis_type == "distribution_analysis":
                            if not column:
                                result_str = json.dumps({"错误": "distribution_analysis 需要指定 column 参数"}, ensure_ascii=False)
                            else:
                                result_str = distribution_analysis(data_json, column=column, bins=bins)
                        elif analysis_type == "group_analysis":
                            if not group_col or not value_col:
                                result_str = json.dumps({"错误": "group_analysis 需要指定 group_col 和 value_col 参数"}, ensure_ascii=False)
                            else:
                                result_str = group_analysis(data_json, group_col=group_col, value_col=value_col, agg_func=agg_func)
                        else:
                            result_str = json.dumps({"错误": f"未知分析类型: {analysis_type}"}, ensure_ascii=False)
                    except Exception as e:
                        import traceback
                        result_str = json.dumps({"错误": f"分析执行失败: {str(e)}", "traceback": traceback.format_exc()}, ensure_ascii=False)

                elif func_name == "create_chart":
                    chart_type = func_args.get("chart_type", "bar")
                    data_json = func_args.get("data_json", "[]")
                    data = json.loads(data_json)
                    df = pd.DataFrame(data)

                    x_col = func_args.get("x_col", "")
                    y_col = func_args.get("y_col", None)
                    color_col = func_args.get("color_col", None)
                    z_col = func_args.get("z_col", None)
                    title = func_args.get("title", "图表")

                    fig = create_chart(
                        df=df,
                        chart_type=chart_type,
                        x_col=x_col,
                        y_col=y_col,
                        color_col=color_col,
                        z_col=z_col,
                        title=title
                    )
                    figures.append(fig)
                    result_str = f"图表「{title}」(类型: {chart_type}) 已成功生成。"

                else:
                    result_str = f"错误：未知工具 {func_name}"

            except Exception as e:
                import traceback
                result_str = f"工具 {func_name} 执行出错：{str(e)}\n{traceback.format_exc()}"

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result_str
            })

    return "达到最大轮次限制，分析未完成。", figures