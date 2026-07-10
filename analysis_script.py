"""
数据分析脚本模块 - 可作为独立脚本运行，也可被 AI Agent 调用

提供以下分析功能：
1. data_profile        - 数据概览（缺失值、类型、唯一值等）
2. correlation_analysis - 相关性分析
3. statistical_summary - 详细统计摘要
4. detect_outliers     - 异常值检测
5. distribution_analysis - 分布分析
6. group_analysis      - 分组聚合分析
"""

import pandas as pd
import numpy as np
import json
import sys
from typing import Optional, List, Union


def _ensure_df(df_or_json: Union[str, pd.DataFrame]) -> pd.DataFrame:
    """统一入口：接受 DataFrame 或 JSON 字符串，返回 DataFrame"""
    if isinstance(df_or_json, pd.DataFrame):
        return df_or_json
    return pd.DataFrame(json.loads(df_or_json))



def data_profile(df_json: str) -> str:
    """
    数据概览分析：返回数据集的完整画像报告

    Args:
        df_json: 数据的 JSON 字符串（由 get_data_full 获取），或直接传 DataFrame

    Returns:
        JSON 字符串，包含行数、列数、每列的缺失值/类型/唯一值/描述性统计
    """
    df = _ensure_df(df_json)

    profile = {
        "行数": len(df),
        "列数": len(df.columns),
        "内存占用": f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB",
    }

    columns_info = []
    for col in df.columns:
        info = {
            "列名": col,
            "类型": str(df[col].dtype),
            "非空值": int(df[col].count()),
            "缺失值": int(df[col].isna().sum()),
            "缺失率": f"{df[col].isna().mean() * 100:.1f}%",
            "唯一值数": int(df[col].nunique()),
        }

        # 数值列额外统计
        if pd.api.types.is_numeric_dtype(df[col]):
            s = df[col].dropna()
            if len(s) > 0:
                info.update({
                    "最小值": round(float(s.min()), 4),
                    "最大值": round(float(s.max()), 4),
                    "均值": round(float(s.mean()), 4),
                    "中位数": round(float(s.median()), 4),
                    "标准差": round(float(s.std()), 4) if len(s) > 1 else 0,
                    "偏度": round(float(s.skew()), 4) if len(s) > 2 else 0,
                    "峰度": round(float(s.kurt()), 4) if len(s) > 2 else 0,
                    "25%分位": round(float(s.quantile(0.25)), 4),
                    "75%分位": round(float(s.quantile(0.75)), 4),
                })

        # 文本列显示前几个唯一值
        if df[col].dtype == 'object':
            top_values = df[col].value_counts().head(5).to_dict()
            info["前5高频值"] = {str(k): int(v) for k, v in top_values.items()}

        columns_info.append(info)

    profile["列信息"] = columns_info

    # 重复行检测
    dup_count = df.duplicated().sum()
    profile["重复行数"] = int(dup_count)
    profile["重复率"] = f"{dup_count / len(df) * 100:.1f}%" if len(df) > 0 else "0%"

    return json.dumps(profile, ensure_ascii=False, indent=2)


def correlation_analysis(df_json: str, method: str = "pearson") -> str:
    """
    相关性分析：计算数值列之间的相关系数矩阵

    Args:
        df_json: 数据的 JSON 字符串，或直接传 DataFrame
        method: 相关方法（pearson / spearman / kendall）

    Returns:
        JSON 字符串，包含相关系数矩阵和高相关对
    """
    df = _ensure_df(df_json)
    num_df = df.select_dtypes(include="number")

    if num_df.shape[1] < 2:
        return json.dumps({"错误": "需要至少2个数值列才能计算相关性"}, ensure_ascii=False)

    corr = num_df.corr(method=method)

    # 找出高相关对（|r| > 0.7）
    high_corr = []
    cols = corr.columns
    for i in range(len(cols)):
        for j in range(i + 1, len(cols)):
            val = corr.iloc[i, j]
            if abs(val) >= 0.7:
                high_corr.append({
                    "列1": cols[i],
                    "列2": cols[j],
                    f"{method}相关系数": round(float(val), 4),
                    "相关强度": "强正相关" if val > 0 else "强负相关"
                })

    # 按绝对值排序
    high_corr.sort(key=lambda x: abs(x[f"{method}相关系数"]), reverse=True)

    result = {
        "方法": method,
        "参与列数": num_df.shape[1],
        "参与列名": list(num_df.columns),
        "相关系数矩阵": corr.round(4).to_dict(),
        "高相关对 (|r|≥0.7)": high_corr[:20],  # 最多显示20对
    }

    if not high_corr:
        result["高相关对 (|r|≥0.7)"] = "未发现强相关性"

    return json.dumps(result, ensure_ascii=False, indent=2)


def statistical_summary(df_json: str, columns: Optional[List[str]] = None) -> str:
    """
    详细统计摘要：对指定列（或所有数值列）进行详细统计分析

    Args:
        df_json: 数据的 JSON 字符串，或直接传 DataFrame
        columns: 要分析的列名列表（可选，不传则分析所有数值列）

    Returns:
        JSON 字符串，包含每列的详细统计信息
    """
    df = _ensure_df(df_json)

    if columns:
        valid_cols = [c for c in columns if c in df.columns]
        if not valid_cols:
            return json.dumps({"错误": f"指定的列 {columns} 都不存在于数据表中，可用列: {list(df.columns)}"},
                            ensure_ascii=False)
        target_cols = valid_cols
    else:
        target_cols = list(df.select_dtypes(include="number").columns)
        if not target_cols:
            target_cols = list(df.columns)

    results = {}
    for col in target_cols:
        s = df[col].dropna()
        info = {
            "列名": col,
            "类型": str(df[col].dtype),
            "非空数": int(len(s)),
            "缺失数": int(df[col].isna().sum()),
        }

        if pd.api.types.is_numeric_dtype(s):
            info.update({
                "最小值": round(float(s.min()), 4),
                "最大值": round(float(s.max()), 4),
                "极差": round(float(s.max() - s.min()), 4),
                "均值": round(float(s.mean()), 4),
                "中位数": round(float(s.median()), 4),
                "众数": s.mode().tolist()[:3] if len(s.mode()) > 0 else [],
                "标准差": round(float(s.std()), 4) if len(s) > 1 else 0,
                "方差": round(float(s.var()), 4) if len(s) > 1 else 0,
                "偏度": round(float(s.skew()), 4) if len(s) > 2 else 0,
                "峰度": round(float(s.kurt()), 4) if len(s) > 2 else 0,
                "25%分位": round(float(s.quantile(0.25)), 4),
                "50%分位": round(float(s.quantile(0.50)), 4),
                "75%分位": round(float(s.quantile(0.75)), 4),
                "90%分位": round(float(s.quantile(0.90)), 4),
                "95%分位": round(float(s.quantile(0.95)), 4),
                "99%分位": round(float(s.quantile(0.99)), 4),
                "变异系数": round(float(s.std() / s.mean()), 4) if s.mean() != 0 else None,
            })
        elif df[col].dtype == 'object':
            value_counts = s.value_counts()
            info.update({
                "唯一值数": int(s.nunique()),
                "前5高频值": {str(k): int(v) for k, v in value_counts.head(5).to_dict().items()},
                "频率占比": {str(k): f"{v / len(s) * 100:.1f}%"
                          for k, v in value_counts.head(5).to_dict().items()},
            })

        results[col] = info

    return json.dumps({"统计摘要": results}, ensure_ascii=False, indent=2)


def detect_outliers(df_json: str, column: str, method: str = "iqr", threshold: float = 1.5) -> str:
    """
    异常值检测：使用 IQR 或 Z-Score 方法检测指定列的异常值

    Args:
        df_json: 数据的 JSON 字符串，或直接传 DataFrame
        column: 要检测的列名
        method: 检测方法（iqr / zscore）
        threshold: 阈值（IQR 默认1.5，Z-Score 默认3）

    Returns:
        JSON 字符串，包含异常值详细信息
    """
    df = _ensure_df(df_json)

    if column not in df.columns:
        return json.dumps({"错误": f"列 '{column}' 不存在，可用列: {list(df.columns)}"},
                        ensure_ascii=False)

    s = df[column].dropna()

    if not pd.api.types.is_numeric_dtype(s):
        return json.dumps({"错误": f"列 '{column}' 不是数值类型，无法检测异常值"},
                        ensure_ascii=False)

    if method == "iqr":
        Q1 = s.quantile(0.25)
        Q3 = s.quantile(0.75)
        IQR = Q3 - Q1
        lower = Q1 - threshold * IQR
        upper = Q3 + threshold * IQR
        outliers = s[(s < lower) | (s > upper)]
        method_desc = f"IQR 方法 (阈值={threshold})，下界={lower:.4f}，上界={upper:.4f}"

    elif method == "zscore":
        mean = s.mean()
        std = s.std()
        z_scores = (s - mean) / std
        outliers = s[abs(z_scores) > threshold]
        method_desc = f"Z-Score 方法 (阈值={threshold})"
        lower = mean - threshold * std
        upper = mean + threshold * std

    else:
        return json.dumps({"错误": f"不支持的检测方法: {method}，可选: iqr, zscore"},
                        ensure_ascii=False)

    result = {
        "检测列": column,
        "检测方法": method_desc,
        "总数据量": int(len(s)),
        "异常值数": int(len(outliers)),
        "异常值比例": f"{len(outliers) / len(s) * 100:.2f}%" if len(s) > 0 else "0%",
        "正常范围": {
            "下界": round(float(lower), 4),
            "上界": round(float(upper), 4),
        },
        "异常值统计": {
            "最小值": round(float(outliers.min()), 4) if len(outliers) > 0 else None,
            "最大值": round(float(outliers.max()), 4) if len(outliers) > 0 else None,
            "均值": round(float(outliers.mean()), 4) if len(outliers) > 0 else None,
        },
        "异常值索引与数值": outliers.head(30).to_dict() if len(outliers) > 0 else "无异常值",
    }

    # 如果异常值太多，截断显示
    if len(outliers) > 30:
        result["异常值索引与数值"] = {
            "注意": f"异常值数量({len(outliers)})过多，仅显示前30个",
            **outliers.head(30).to_dict()
        }

    return json.dumps(result, ensure_ascii=False, indent=2)


def distribution_analysis(df_json: str, column: str, bins: int = 10) -> str:
    """
    分布分析：分析指定列的分布特征

    Args:
        df_json: 数据的 JSON 字符串，或直接传 DataFrame
        column: 要分析的列名
        bins: 分箱数（仅数值列有效，默认10）

    Returns:
        JSON 字符串，包含分箱/频数分布信息
    """
    df = _ensure_df(df_json)

    if column not in df.columns:
        return json.dumps({"错误": f"列 '{column}' 不存在，可用列: {list(df.columns)}"},
                        ensure_ascii=False)

    s = df[column].dropna()

    result = {"列名": column, "类型": str(df[column].dtype), "非空数": int(len(s))}

    if pd.api.types.is_numeric_dtype(s):
        # 数值分布：分箱统计
        counts, edges = np.histogram(s, bins=bins)
        bins_info = []
        for i in range(len(counts)):
            bins_info.append({
                "区间": f"[{edges[i]:.4f}, {edges[i+1]:.4f})",
                "频数": int(counts[i]),
                "占比": f"{counts[i] / len(s) * 100:.1f}%",
            })

        # 累积分布
        cumsum = np.cumsum(counts)

        result.update({
            "最小值": round(float(s.min()), 4),
            "最大值": round(float(s.max()), 4),
            "分箱数": bins,
            "分箱分布": bins_info,
            "累积分布": [f"{int(c)} ({c/len(s)*100:.1f}%)" for c in cumsum],
            "偏度": round(float(s.skew()), 4) if len(s) > 2 else 0,
            "分布形态": "右偏" if s.skew() > 0.5 else ("左偏" if s.skew() < -0.5 else "近似对称"),
        })

    elif df[column].dtype == 'object':
        # 类别分布
        value_counts = s.value_counts()
        total = len(s)
        categories = []
        for val, count in value_counts.items():
            categories.append({
                "值": str(val),
                "频数": int(count),
                "占比": f"{count / total * 100:.1f}%",
            })

        result.update({
            "唯一值数": int(s.nunique()),
            "类别分布": categories[:30],  # 最多显示30个类别
        })

        if s.nunique() > 30:
            result["注意"] = f"类别过多({s.nunique()})，仅显示前30个"

    return json.dumps(result, ensure_ascii=False, indent=2)


def group_analysis(df_json: str, group_col: str, value_col: str, agg_func: str = "mean") -> str:
    """
    分组聚合分析：按指定列分组，对数值列进行聚合计算

    Args:
        df_json: 数据的 JSON 字符串，或直接传 DataFrame
        group_col: 分组列名
        value_col: 数值列名
        agg_func: 聚合函数（mean / sum / count / max / min / std / median）

    Returns:
        JSON 字符串，包含分组聚合结果
    """
    df = _ensure_df(df_json)

    if group_col not in df.columns:
        return json.dumps({"错误": f"列 '{group_col}' 不存在，可用列: {list(df.columns)}"},
                        ensure_ascii=False)

    if value_col not in df.columns:
        return json.dumps({"错误": f"列 '{value_col}' 不存在，可用列: {list(df.columns)}"},
                        ensure_ascii=False)

    valid_funcs = {"mean", "sum", "count", "max", "min", "std", "median"}
    if agg_func not in valid_funcs:
        return json.dumps({"错误": f"不支持的聚合函数: {agg_func}，可选: {valid_funcs}"},
                        ensure_ascii=False)

    grouped = df.groupby(group_col)[value_col].agg(agg_func).reset_index()
    grouped = grouped.sort_values(value_col, ascending=False)

    result = {
        "分组列": group_col,
        "数值列": value_col,
        "聚合函数": agg_func,
        "分组数": int(grouped[group_col].nunique()),
        "结果": grouped.head(50).to_dict(orient="records"),
    }

    if len(grouped) > 50:
        result["注意"] = f"分组过多({len(grouped)})，仅显示前50组"

    # 补充总体统计
    s = df[value_col].dropna()
    result["总体统计"] = {
        "总体均值": round(float(s.mean()), 4),
        "总体标准差": round(float(s.std()), 4) if len(s) > 1 else 0,
        "最大值组": grouped.iloc[0].to_dict() if len(grouped) > 0 else None,
        "最小值组": grouped.iloc[-1].to_dict() if len(grouped) > 0 else None,
    }

    return json.dumps(result, ensure_ascii=False, indent=2)


def main():
    """
    独立运行模式：从命令行参数读取输入并执行分析
    用法: python analysis_script.py <function_name> <json_args>
    """
    if len(sys.argv) < 3:
        print(json.dumps({
            "用法": "python analysis_script.py <函数名> '<JSON参数>'",
            "可用函数": [
                "data_profile",
                "correlation_analysis",
                "statistical_summary",
                "detect_outliers",
                "distribution_analysis",
                "group_analysis",
            ],
            "示例": "python analysis_script.py data_profile '[{\"col1\": 1, \"col2\": \"a\"}]'"
        }, ensure_ascii=False, indent=2))
        return

    func_name = sys.argv[1]
    # 拼接剩余参数（兼容 cmd.exe 引号处理导致的 JSON 截断）
    args_json = " ".join(sys.argv[2:])

    try:
        parsed = json.loads(args_json)
    except json.JSONDecodeError as e:
        print(json.dumps({"错误": f"JSON 解析失败: {e}"}, ensure_ascii=False))
        return

    functions = {
        "data_profile": data_profile,
        "correlation_analysis": correlation_analysis,
        "statistical_summary": statistical_summary,
        "detect_outliers": detect_outliers,
        "distribution_analysis": distribution_analysis,
        "group_analysis": group_analysis,
    }

    if func_name not in functions:
        print(json.dumps({
            "错误": f"未知函数: {func_name}",
            "可用函数": list(functions.keys())
        }, ensure_ascii=False))
        return

    try:
        # 支持两种调用方式：
        # 1. 直接传 JSON 数组 -> 作为 df_json 参数（适用于只需要数据的函数）
        # 2. 传 JSON 对象 -> 作为 **kwargs 展开
        if isinstance(parsed, list):
            result = functions[func_name](json.dumps(parsed))
        elif isinstance(parsed, dict):
            result = functions[func_name](**parsed)
        else:
            result = functions[func_name](str(parsed))
        print(result)
    except Exception as e:
        print(json.dumps({"错误": f"执行失败: {str(e)}"}, ensure_ascii=False))


if __name__ == "__main__":
    main()