"""
MCP反馈系统
提供智能体行为自我评估和反馈收集功能
"""
import os
import json
import time
import datetime
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

class MCPFeedback:
    """
    MCP反馈系统
    
    用于收集、存储和分析智能体行为的反馈数据
    支持自我评估和用户反馈
    """
    
    def __init__(self, agent_name: str = "default", storage_path: Optional[str] = None):
        """初始化反馈系统
        
        Args:
            agent_name: 智能体名称
            storage_path: 反馈存储路径
        """
        self.agent_name = agent_name
        
        # 设置默认存储路径
        if not storage_path:
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".config", "mcp_feedback")
            os.makedirs(config_dir, exist_ok=True)
            self.storage_path = os.path.join(config_dir, f"{agent_name}_feedback.json")
        else:
            self.storage_path = storage_path
        
        # 初始化反馈数据
        self.feedback_data = self._load_feedback_data()
    
    def _load_feedback_data(self) -> Dict:
        """加载反馈数据
        
        Returns:
            反馈数据
        """
        if os.path.exists(self.storage_path):
            try:
                with open(self.storage_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        
        # 返回默认数据结构
        return {
            "agent_name": self.agent_name,
            "session_feedback": [],
            "historical_stats": {
                "total_sessions": 0,
                "average_rating": 0,
                "total_self_assessments": 0,
                "average_self_score": 0,
                "strengths": {},
                "improvement_areas": {}
            }
        }
    
    def _save_feedback_data(self):
        """保存反馈数据"""
        os.makedirs(os.path.dirname(self.storage_path), exist_ok=True)
        with open(self.storage_path, 'w', encoding='utf-8') as f:
            json.dump(self.feedback_data, f, ensure_ascii=False, indent=2)
    
    async def add_user_feedback(self, 
                         session_id: str,
                         rating: int,
                         comments: Optional[str] = None,
                         strengths: Optional[List[str]] = None,
                         improvement_areas: Optional[List[str]] = None,
                         metadata: Optional[Dict] = None) -> Dict:
        """添加用户反馈
        
        Args:
            session_id: 会话ID
            rating: 评分 (1-5)
            comments: 反馈评论
            strengths: 智能体的优点
            improvement_areas: 需要改进的方面
            metadata: 额外元数据
            
        Returns:
            反馈记录
        """
        # 验证评分范围
        rating = max(1, min(5, rating))
        
        # 创建反馈记录
        feedback = {
            "id": f"fb_{int(time.time())}_{hash(str(session_id))}",
            "session_id": session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "user",
            "rating": rating,
            "comments": comments or "",
            "strengths": strengths or [],
            "improvement_areas": improvement_areas or [],
            "metadata": metadata or {}
        }
        
        # 添加到反馈数据
        self.feedback_data["session_feedback"].append(feedback)
        
        # 更新统计数据
        stats = self.feedback_data["historical_stats"]
        stats["total_sessions"] += 1
        
        # 更新平均评分
        total_ratings = stats["average_rating"] * (stats["total_sessions"] - 1) + rating
        stats["average_rating"] = total_ratings / stats["total_sessions"]
        
        # 更新优点和改进方面的频率
        if strengths:
            for strength in strengths:
                stats["strengths"][strength] = stats["strengths"].get(strength, 0) + 1
        
        if improvement_areas:
            for area in improvement_areas:
                stats["improvement_areas"][area] = stats["improvement_areas"].get(area, 0) + 1
        
        # 保存数据
        self._save_feedback_data()
        
        return feedback
    
    async def add_self_assessment(self,
                           session_id: str,
                           prompt: str,
                           response: str,
                           score: float,
                           rationale: Optional[str] = None,
                           strengths: Optional[List[str]] = None,
                           improvement_areas: Optional[List[str]] = None,
                           metadata: Optional[Dict] = None) -> Dict:
        """添加自我评估
        
        Args:
            session_id: 会话ID
            prompt: 提示
            response: 响应
            score: 自评分数 (0.0-1.0)
            rationale: 评分理由
            strengths: 回答的优点
            improvement_areas: 需要改进的方面
            metadata: 额外元数据
            
        Returns:
            评估记录
        """
        # 验证分数范围
        score = max(0.0, min(1.0, score))
        
        # 创建评估记录
        assessment = {
            "id": f"sa_{int(time.time())}_{hash(str(session_id))}",
            "session_id": session_id,
            "timestamp": datetime.datetime.now().isoformat(),
            "type": "self",
            "prompt": prompt,
            "response": response,
            "score": score,
            "rationale": rationale or "",
            "strengths": strengths or [],
            "improvement_areas": improvement_areas or [],
            "metadata": metadata or {}
        }
        
        # 添加到反馈数据
        self.feedback_data["session_feedback"].append(assessment)
        
        # 更新统计数据
        stats = self.feedback_data["historical_stats"]
        stats["total_self_assessments"] += 1
        
        # 更新平均自评分
        total_scores = stats["average_self_score"] * (stats["total_self_assessments"] - 1) + score
        stats["average_self_score"] = total_scores / stats["total_self_assessments"]
        
        # 保存数据
        self._save_feedback_data()
        
        return assessment
    
    async def get_session_feedback(self, session_id: str) -> List[Dict]:
        """获取会话反馈
        
        Args:
            session_id: 会话ID
            
        Returns:
            会话反馈列表
        """
        return [
            feedback for feedback in self.feedback_data["session_feedback"]
            if feedback["session_id"] == session_id
        ]
    
    async def get_feedback_summary(self, lookback_days: int = 30) -> Dict:
        """获取反馈摘要
        
        Args:
            lookback_days: 回顾天数
            
        Returns:
            反馈摘要
        """
        # 计算时间限制
        current_time = datetime.datetime.now()
        time_limit = (current_time - datetime.timedelta(days=lookback_days)).isoformat()
        
        # 筛选最近的反馈
        recent_feedback = [
            feedback for feedback in self.feedback_data["session_feedback"]
            if feedback["timestamp"] >= time_limit
        ]
        
        # 分离用户反馈和自我评估
        user_feedback = [fb for fb in recent_feedback if fb["type"] == "user"]
        self_assessments = [fb for fb in recent_feedback if fb["type"] == "self"]
        
        # 计算统计数据
        user_ratings = [fb["rating"] for fb in user_feedback if "rating" in fb]
        self_scores = [fb["score"] for fb in self_assessments if "score" in fb]
        
        avg_user_rating = sum(user_ratings) / len(user_ratings) if user_ratings else 0
        avg_self_score = sum(self_scores) / len(self_scores) if self_scores else 0
        
        # 收集优点和改进方面
        strengths = {}
        improvement_areas = {}
        
        for fb in recent_feedback:
            for strength in fb.get("strengths", []):
                strengths[strength] = strengths.get(strength, 0) + 1
            
            for area in fb.get("improvement_areas", []):
                improvement_areas[area] = improvement_areas.get(area, 0) + 1
        
        # 排序
        sorted_strengths = sorted(strengths.items(), key=lambda x: x[1], reverse=True)
        sorted_improvements = sorted(improvement_areas.items(), key=lambda x: x[1], reverse=True)
        
        return {
            "period_days": lookback_days,
            "total_feedback": len(recent_feedback),
            "user_feedback_count": len(user_feedback),
            "self_assessment_count": len(self_assessments),
            "average_user_rating": avg_user_rating,
            "average_self_score": avg_self_score,
            "top_strengths": sorted_strengths[:5],
            "top_improvement_areas": sorted_improvements[:5],
            "all_time_stats": self.feedback_data["historical_stats"]
        }
    
    async def get_performance_trends(self, interval: str = "week") -> Dict:
        """获取性能趋势
        
        Args:
            interval: 时间间隔 ("day", "week", "month")
            
        Returns:
            性能趋势数据
        """
        # 确定时间单位
        if interval == "day":
            time_format = "%Y-%m-%d"
            td = datetime.timedelta(days=1)
        elif interval == "week":
            time_format = "%Y-%W"  # 年-周数
            td = datetime.timedelta(days=7)
        else:  # month
            time_format = "%Y-%m"
            td = datetime.timedelta(days=30)
        
        # 初始化数据结构
        trend_data = {}
        
        # 处理所有反馈
        for feedback in self.feedback_data["session_feedback"]:
            try:
                # 解析时间戳
                timestamp = datetime.datetime.fromisoformat(feedback["timestamp"])
                time_key = timestamp.strftime(time_format)
                
                # 初始化时间点数据
                if time_key not in trend_data:
                    trend_data[time_key] = {
                        "user_ratings": [],
                        "self_scores": [],
                        "count": 0
                    }
                
                # 添加数据
                trend_data[time_key]["count"] += 1
                if feedback["type"] == "user" and "rating" in feedback:
                    trend_data[time_key]["user_ratings"].append(feedback["rating"])
                elif feedback["type"] == "self" and "score" in feedback:
                    trend_data[time_key]["self_scores"].append(feedback["score"])
            except (ValueError, KeyError):
                # 跳过无效数据
                continue
        
        # 计算每个时间点的平均值
        result = []
        for time_key, data in trend_data.items():
            avg_user_rating = sum(data["user_ratings"]) / len(data["user_ratings"]) if data["user_ratings"] else None
            avg_self_score = sum(data["self_scores"]) / len(data["self_scores"]) if data["self_scores"] else None
            
            result.append({
                "time_period": time_key,
                "feedback_count": data["count"],
                "average_user_rating": avg_user_rating,
                "average_self_score": avg_self_score
            })
        
        # 按时间排序
        result.sort(key=lambda x: x["time_period"])
        
        return {
            "interval": interval,
            "trend_data": result
        }


class SelfEvaluator:
    """
    智能体自我评估器
    
    提供智能体回答质量的自动评估
    """
    
    def __init__(self, llm_service = None):
        """初始化自我评估器
        
        Args:
            llm_service: 语言模型服务
        """
        self.llm_service = llm_service
    
    async def evaluate_response(self, 
                         prompt: str, 
                         response: str,
                         context: Optional[str] = None) -> Dict:
        """评估智能体的回答质量
        
        Args:
            prompt: 用户提示
            response: 智能体回答
            context: 可选的上下文信息
            
        Returns:
            评估结果
        """
        if not self.llm_service:
            # 无LLM服务时返回默认评估
            return {
                "score": 0.7,
                "rationale": "没有LLM服务可用于评估回答质量",
                "strengths": ["无法确定优点"],
                "improvements": ["无法确定改进点"]
            }
        
        # 构建评估提示
        eval_prompt = f"""你是一个严格的AI回答质量评估专家。请评估以下AI回答的质量:

用户查询: {prompt}

AI回答:
{response}

"""
        
        if context:
            eval_prompt += f"""
相关上下文:
{context}

"""
        
        eval_prompt += """
请评估回答的以下方面:
1. 准确性: 回答是否基于事实和准确信息
2. 完整性: 回答是否全面回应了用户的查询
3. 清晰度: 回答是否表达清晰、结构良好
4. 相关性: 回答是否直接针对用户的查询
5. 有用性: 回答对用户是否有实际帮助

请提供:
1. 总体得分 (0.0-1.0，1.0代表完美回答)
2. 评分理由，简明扼要地解释得分
3. 回答的2-3个主要优点
4. 2-3个可改进的方面

请以JSON格式返回，包含以下字段: score, rationale, strengths, improvements
"""
        
        try:
            # 调用LLM进行评估
            response = await self.llm_service.generate(
                messages=[
                    {"role": "system", "content": "你是一个专业的回答质量评估专家。请严格、客观地评估AI回答的质量，并提供有建设性的反馈。"},
                    {"role": "user", "content": eval_prompt}
                ],
                max_tokens=1024
            )
            
            # 提取JSON评估结果
            content = response.get("content", "")
            
            # 解析JSON
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', content)
            if json_match:
                json_str = json_match.group(1)
            else:
                # 尝试直接解析
                json_str = content
                
            try:
                evaluation = json.loads(json_str)
                
                # 验证和标准化结果
                score = float(evaluation.get("score", 0.7))
                score = max(0.0, min(1.0, score))
                
                return {
                    "score": score,
                    "rationale": evaluation.get("rationale", "无评分理由"),
                    "strengths": evaluation.get("strengths", []),
                    "improvements": evaluation.get("improvements", [])
                }
            
            except json.JSONDecodeError:
                # 解析失败，进行手动提取
                score_match = re.search(r'score["\']?\s*:\s*([0-9.]+)', content)
                score = float(score_match.group(1)) if score_match else 0.7
                score = max(0.0, min(1.0, score))
                
                return {
                    "score": score,
                    "rationale": "无法解析完整评估结果",
                    "strengths": ["无法提取优点"],
                    "improvements": ["无法提取改进点"]
                }
            
        except Exception as e:
            # 评估出错，返回默认值
            return {
                "score": 0.7,
                "rationale": f"评估过程出错: {str(e)}",
                "strengths": ["无法确定优点"],
                "improvements": ["无法确定改进点"]
            }
