"""Fixed presentation inputs, not relevance labels, expected ranks, or historical claims."""

from typing import TypedDict


class DemoSpec(TypedDict):
    id: str
    title: str
    description: str
    source_note: str
    text_query: str
    figure_keys: tuple[str, str]
    bbox: dict[str, float]
    limitations: list[str]


DOMESTIC_CASES: tuple[DemoSpec, ...] = (
    {
        "id": "gengzhi-loom",
        "title": "《耕织图》：织机与经线",
        "description": "比较室内织机与大型织机画面的支架、经线及操作者。场景名来自 AI 整理。",
        "source_note": "国内出版来源：中华再造善本 / 国家图书馆出版社；Commons 提供扫描文件。",
        "text_query": "织机 经线",
        "figure_keys": ("ai-zhsy-p24-loom", "ai-zhsy-p26-large-loom"),
        "bbox": {"x": 0.025, "y": 0.35, "width": 0.24, "height": 0.32},
        "limitations": [
            "扫描分辨率较低；不能确认具体织机型号、织法或提花结构。",
            "固定图对用于讲解，不是人工相关性正例或已证实的历史传承。",
        ],
    },
    {
        "id": "tiangong-waterpower",
        "title": "《天工开物》：水碓与水磨",
        "description": (
            "比较水轮动力下的两幅谷物加工机械，观察往复舂击与磨盘加工的结构差别。解释仍属 AI 推断。"
        ),
        "source_note": "国内馆藏来源：中国国家图书馆数字古籍；不标记为现代国内出版版本。",
        "text_query": "水轮 驱动 谷物 加工",
        "figure_keys": ("ai-nlc-p25-water-pestle", "ai-nlc-p26-water-mill"),
        "bbox": {"x": 0.055, "y": 0.16, "width": 0.9, "height": 0.73},
        "limitations": [
            "原扫描和国图水印保留；图题转录及机械解释尚未人工校订。",
            "共享水轮外形不等于功能相同，也不证明历史传承。",
        ],
    },
)
