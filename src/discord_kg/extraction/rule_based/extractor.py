"""
Step 3: Entity & Relation Extraction Layer
Implementation according to src/discord_kg/extraction/README.md specification

This module processes classified Discord messages and extracts structured triples
(subject, predicate, object) using message type-specific strategies.
"""

import json
import re
import datetime
import os
from typing import List, Dict, Tuple, Optional, Any
from dataclasses import dataclass, asdict
import logging

class NumpyEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles numpy data types."""
    def default(self, obj):
        try:
            import numpy as np
            if isinstance(obj, (np.integer, np.floating, np.bool_)):
                return obj.item()
            elif isinstance(obj, np.ndarray):
                return obj.tolist()
        except ImportError:
            pass
        return super().default(obj)

logger = logging.getLogger(__name__)


@dataclass
class Triple:
    """Knowledge graph triple with metadata according to README spec."""
    subject: str
    predicate: str
    object: str
    message_id: str
    segment_id: str
    timestamp: str
    confidence: float
    
    def to_dict(self) -> Dict[str, Any]:
        result = asdict(self)
        # Ensure confidence is JSON serializable
        try:
            import numpy as np
            if isinstance(result['confidence'], (np.float32, np.float64)):
                result['confidence'] = float(result['confidence'])
        except ImportError:
            pass
        return result


class MessageTypeExtractor:
    """Extraction strategies by message type as per README specification."""
    
    def __init__(self):
        # Financial/trading patterns
        self.asset_patterns = {
            'crypto': re.compile(r'\b(btc|bitcoin|eth|ethereum|ada|cardano|sol|solana)\b', re.IGNORECASE),
            'etf': re.compile(r'\b(tqqq|sqqq|spy|qqq|vti|voo|arkk|arkf|arkg)\b', re.IGNORECASE),
            'stock': re.compile(r'\b(aapl|tsla|msft|amzn|googl|nvda|meta)\b', re.IGNORECASE)
        }
        
        self.strategy_patterns = re.compile(
            r'\b(covered call|iron condor|wheel|dca|dollar cost|symphony|algorithm|backtest)\b', 
            re.IGNORECASE
        )
        
        self.action_patterns = {
            'buy': re.compile(r'\b(buy|buying|bought|long|bullish)\b', re.IGNORECASE),
            'sell': re.compile(r'\b(sell|selling|sold|short|bearish)\b', re.IGNORECASE),
            'hold': re.compile(r'\b(hold|holding|hodl|keep)\b', re.IGNORECASE)
        }
        
        self.performance_pattern = re.compile(r'([+-]?\d+(?:\.\d+)?)\s*%')
        self.platform_pattern = re.compile(r'\b(composer|stonks\.com|robinhood|fidelity)\b', re.IGNORECASE)
    
    def extract_question_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract asks_about triples from question-type messages."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        # Question indicators
        question_indicators = [
            r'\?',  # Contains question mark
            r'\b(what|how|when|where|why|which|can|could|should|would)\b',
            r'\b(any|anyone|advice|help|thoughts|opinions)\b'
        ]
        
        is_question = any(re.search(pattern, content, re.IGNORECASE) for pattern in question_indicators)
        
        if is_question or message['type'] == 'question':
            # Extract topic - clean up and truncate if needed
            topic = re.sub(r'\b(what|how|when|where|why|which|can|could|should|would|is|are|do|does|did)\b', '', content, flags=re.IGNORECASE)
            topic = topic.strip()
            if len(topic) > 80:
                topic = topic[:80] + '...'
            
            # Handle empty topic
            if not topic.strip():
                topic = content[:60] + '...' if len(content) > 60 else content
                
            triple = Triple(
                subject=author,
                predicate='asks_about',
                object=topic,
                message_id=message['message_id'],
                segment_id=message['segment_id'],
                timestamp=message['timestamp'],
                confidence=0.85
            )
            triples.append(triple)
            
        return triples
    
    def extract_answer_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract answer-related triples. Q&A linking handled separately."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        if message['type'] == 'answer':
            # Extract any specific recommendations or statements
            assets = self._extract_assets(content)
            strategies = self.strategy_patterns.findall(content)
            
            # Create provides_info triples for answers
            info_content = content[:60] + '...' if len(content) > 60 else content
            triple = Triple(
                subject=author,
                predicate='provides_info',
                object=info_content,
                message_id=message['message_id'],
                segment_id=message['segment_id'],
                timestamp=message['timestamp'],
                confidence=0.75
            )
            triples.append(triple)
            
        return triples
    
    def extract_alert_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract alert triples using rule-based patterns."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        # Alert indicators for financial contexts
        alert_patterns = [
            r'\b(alert|warning|notice|reminder|announcement)\b',
            r'\b(fomc|fed|cpi|inflation|earnings|report|meeting)\b',
            r'\b(volatility|expected|caution|watch|attention)\b'
        ]
        
        is_alert = any(re.search(pattern, content, re.IGNORECASE) for pattern in alert_patterns)
        
        if is_alert or message['type'] == 'alert':
            # Extract alert topic
            alert_topic = content[:60] + '...' if len(content) > 60 else content
            
            triple = Triple(
                subject=author,
                predicate='alerts',
                object=f"all_members about {alert_topic}",
                message_id=message['message_id'],
                segment_id=message['segment_id'],
                timestamp=message['timestamp'],
                confidence=0.80
            )
            triples.append(triple)
            
        return triples
    
    def extract_strategy_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract strategy discussion triples using LLM + rule-based approach."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        # Find strategy mentions
        strategies = self.strategy_patterns.findall(content)
        
        for strategy in strategies:
            triple = Triple(
                subject=author,
                predicate='recommends',
                object=f"{strategy.lower()} strategy",
                message_id=message['message_id'],
                segment_id=message['segment_id'],
                timestamp=message['timestamp'],
                confidence=0.85
            )
            triples.append(triple)
            
        # If classified as strategy but no specific strategy found
        if message['type'] == 'strategy' and not strategies:
            strategy_content = content[:50] + '...' if len(content) > 50 else content
            triple = Triple(
                subject=author,
                predicate='discusses_strategy',
                object=strategy_content,
                message_id=message['message_id'],
                segment_id=message['segment_id'],
                timestamp=message['timestamp'],
                confidence=0.70
            )
            triples.append(triple)
            
        return triples
    
    def extract_signal_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract trading signals using NER + pattern matching."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        # Extract assets and actions
        assets = self._extract_assets(content)
        actions = self._extract_actions(content)
        
        # Create signal triples
        for asset in assets:
            for action in actions:
                predicate = f"recommends_{action}"
                triple = Triple(
                    subject=author,
                    predicate=predicate,
                    object=asset,
                    message_id=message['message_id'],
                    segment_id=message['segment_id'],
                    timestamp=message['timestamp'],
                    confidence=0.80
                )
                triples.append(triple)
                
        # If assets mentioned but no actions, create general mention
        if assets and not actions:
            for asset in assets:
                triple = Triple(
                    subject=author,
                    predicate='mentions_asset',
                    object=asset,
                    message_id=message['message_id'],
                    segment_id=message['segment_id'],
                    timestamp=message['timestamp'],
                    confidence=0.60
                )
                triples.append(triple)
                
        return triples
    
    def extract_performance_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract performance metrics using regex patterns."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        # Find percentage returns
        percentages = self.performance_pattern.findall(content)
        return_keywords = re.search(r'\b(profit|loss|gain|return|made|lost|performance)\b', content, re.IGNORECASE)
        
        if percentages and return_keywords:
            for pct in percentages:
                performance_desc = f"+{pct}% on strategy" if not pct.startswith('-') else f"{pct}% loss on strategy"
                
                triple = Triple(
                    subject=author,
                    predicate='reports_return',
                    object=performance_desc,
                    message_id=message['message_id'],
                    segment_id=message['segment_id'],
                    timestamp=message['timestamp'],
                    confidence=0.85
                )
                triples.append(triple)
                
        return triples
    
    def extract_analysis_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract analysis triples using LLM extraction for abstract reasoning."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        # Analysis indicators
        analysis_patterns = [
            r'\b(analyze|analysis|outlook|forecast|predict|expect)\b',
            r'\b(technical|fundamental|chart|trend|pattern)\b',
            r'\b(bullish|bearish|neutral|sideways)\b'
        ]
        
        is_analysis = any(re.search(pattern, content, re.IGNORECASE) for pattern in analysis_patterns)
        
        if is_analysis or message['type'] == 'analysis':
            # Extract assets being analyzed
            assets = self._extract_assets(content)
            
            if assets:
                for asset in assets:
                    triple = Triple(
                        subject=author,
                        predicate='analyzes',
                        object=f"{asset} outlook",
                        message_id=message['message_id'],
                        segment_id=message['segment_id'],
                        timestamp=message['timestamp'],
                        confidence=0.75
                    )
                    triples.append(triple)
            else:
                # General analysis
                analysis_content = content[:60] + '...' if len(content) > 60 else content
                triple = Triple(
                    subject=author,
                    predicate='provides_analysis',
                    object=analysis_content,
                    message_id=message['message_id'],
                    segment_id=message['segment_id'],
                    timestamp=message['timestamp'],
                    confidence=0.70
                )
                triples.append(triple)
                
        return triples
    
    def extract_discussion_triples(self, message: Dict[str, Any]) -> List[Triple]:
        """Extract discussion triples with light pattern matching."""
        triples = []
        content = message['clean_text']
        author = message['author']
        
        if message['type'] == 'discussion':
            # Extract topics being discussed
            platforms = self.platform_pattern.findall(content)
            assets = self._extract_assets(content)
            
            # Platform discussions
            for platform in platforms:
                triple = Triple(
                    subject=author,
                    predicate='discusses',
                    object=platform.lower(),
                    message_id=message['message_id'],
                    segment_id=message['segment_id'],
                    timestamp=message['timestamp'],
                    confidence=0.65
                )
                triples.append(triple)
            
            # Asset discussions
            for asset in assets:
                triple = Triple(
                    subject=author,
                    predicate='shares_opinion',
                    object=f"on {asset}",
                    message_id=message['message_id'],
                    segment_id=message['segment_id'],
                    timestamp=message['timestamp'],
                    confidence=0.60
                )
                triples.append(triple)
                
        return triples
    
    def _extract_assets(self, content: str) -> List[str]:
        """Extract all asset mentions from content."""
        assets = []
        for asset_type, pattern in self.asset_patterns.items():
            matches = pattern.findall(content)
            assets.extend(matches)
        return list(set([asset.upper() for asset in assets]))
    
    def _extract_actions(self, content: str) -> List[str]:
        """Extract trading actions from content."""
        actions = []
        for action, pattern in self.action_patterns.items():
            if pattern.search(content):
                actions.append(action)
        return actions


class QALinker:
    """Links questions to answers using reply references, mentions, and semantic similarity."""
    
    def __init__(self):
        try:
            from sentence_transformers import SentenceTransformer
            self.sentence_transformer = SentenceTransformer('all-MiniLM-L6-v2')
            self.has_embeddings = True
        except ImportError:
            logger.warning("sentence-transformers not available, using rule-based Q&A linking only")
            self.has_embeddings = False
    
    def link_qa_pairs(self, messages: List[Dict[str, Any]], 
                     time_window_minutes: int = 10,
                     similarity_threshold: float = 0.3) -> List[Triple]:
        """Link questions to answers using multiple strategies."""
        triples = []
        
        # Group messages by segment for context
        segments = {}
        for msg in messages:
            segment_id = msg['segment_id']
            if segment_id not in segments:
                segments[segment_id] = []
            segments[segment_id].append(msg)
        
        logger.info(f"Linking Q&A pairs across {len(segments)} segments")
        
        for segment_id, segment_messages in segments.items():
            segment_messages.sort(key=lambda x: x['timestamp'])
            
            questions = [msg for msg in segment_messages if msg['type'] == 'question']
            answers = [msg for msg in segment_messages if msg['type'] == 'answer']
            
            if not questions or not answers:
                continue
                
            logger.debug(f"Segment {segment_id}: {len(questions)} questions, {len(answers)} answers")
            
            # Strategy 1: Direct reply references
            reply_links = self._link_by_replies(questions, answers)
            triples.extend(reply_links)
            
            # Strategy 2: Mention-based linking
            mention_links = self._link_by_mentions(questions, answers, time_window_minutes)
            triples.extend(mention_links)
            
            # Strategy 3: Semantic similarity (if available)
            if self.has_embeddings:
                semantic_links = self._link_by_similarity(questions, answers, time_window_minutes, similarity_threshold)
                triples.extend(semantic_links)
            
        logger.info(f"Created {len(triples)} Q&A links")
        return triples
    
    def _link_by_replies(self, questions: List[Dict], answers: List[Dict]) -> List[Triple]:
        """Link based on reply_to field."""
        triples = []
        
        for answer in answers:
            reply_to = answer.get('reply_to')
            if reply_to:
                # Find the question this answers
                for question in questions:
                    if question['message_id'] == reply_to:
                        triple = Triple(
                            subject=question['message_id'],
                            predicate='answered_by',
                            object=answer['message_id'],
                            message_id=f"{question['message_id']}_reply_{answer['message_id']}",
                            segment_id=question['segment_id'],
                            timestamp=answer['timestamp'],
                            confidence=0.95  # High confidence for direct replies
                        )
                        triples.append(triple)
                        break
                        
        return triples
    
    def _link_by_mentions(self, questions: List[Dict], answers: List[Dict], time_window_minutes: int) -> List[Triple]:
        """Link based on @mentions in answers."""
        triples = []
        
        for answer in answers:
            mentions = answer.get('mentions', [])
            answer_time = datetime.datetime.fromisoformat(answer['timestamp'].replace('Z', '+00:00'))
            
            for mention in mentions:
                # Find questions from the mentioned user
                for question in questions:
                    if question['author'].lower() == mention.lower():
                        question_time = datetime.datetime.fromisoformat(question['timestamp'].replace('Z', '+00:00'))
                        
                        # Check time window
                        if (answer_time - question_time).total_seconds() <= time_window_minutes * 60:
                            triple = Triple(
                                subject=question['message_id'],
                                predicate='answered_by',
                                object=answer['message_id'],
                                message_id=f"{question['message_id']}_mention_{answer['message_id']}",
                                segment_id=question['segment_id'],
                                timestamp=answer['timestamp'],
                                confidence=0.80  # Good confidence for mentions
                            )
                            triples.append(triple)
                            
        return triples
    
    def _link_by_similarity(self, questions: List[Dict], answers: List[Dict], 
                           time_window_minutes: int, similarity_threshold: float) -> List[Triple]:
        """Link based on semantic similarity of content."""
        if not self.has_embeddings:
            return []
            
        triples = []
        
        try:
            from sklearn.metrics.pairwise import cosine_similarity
            import numpy as np
            
            question_texts = [q['clean_text'] for q in questions]
            answer_texts = [a['clean_text'] for a in answers]
            
            question_embeddings = self.sentence_transformer.encode(question_texts)
            answer_embeddings = self.sentence_transformer.encode(answer_texts)
            
            similarities = cosine_similarity(question_embeddings, answer_embeddings)
            
            for i, question in enumerate(questions):
                for j, answer in enumerate(answers):
                    # Check time constraint
                    q_time = datetime.datetime.fromisoformat(question['timestamp'].replace('Z', '+00:00'))
                    a_time = datetime.datetime.fromisoformat(answer['timestamp'].replace('Z', '+00:00'))
                    
                    if (a_time - q_time).total_seconds() > time_window_minutes * 60:
                        continue
                        
                    if a_time < q_time:  # Answer must come after question
                        continue
                        
                    similarity = similarities[i][j]
                    
                    if similarity > similarity_threshold:
                        triple = Triple(
                            subject=question['message_id'],
                            predicate='answered_by',
                            object=answer['message_id'],
                            message_id=f"{question['message_id']}_semantic_{answer['message_id']}",
                            segment_id=question['segment_id'],
                            timestamp=answer['timestamp'],
                            confidence=float(similarity)
                        )
                        triples.append(triple)
                        
        except Exception as e:
            logger.error(f"Error in semantic linking: {e}")
            
        return triples


class Step3Extractor:
    """Main Step 3 implementation following README specification."""
    
    def __init__(self):
        self.message_extractor = MessageTypeExtractor()
        self.qa_linker = QALinker()
        
        # Message type extraction mapping
        self.extraction_strategies = {
            'question': self.message_extractor.extract_question_triples,
            'answer': self.message_extractor.extract_answer_triples,
            'alert': self.message_extractor.extract_alert_triples,
            'strategy': self.message_extractor.extract_strategy_triples,
            'signal': self.message_extractor.extract_signal_triples,
            'performance': self.message_extractor.extract_performance_triples,
            'analysis': self.message_extractor.extract_analysis_triples,
            'discussion': self.message_extractor.extract_discussion_triples,
        }
    
    def extract_triples(self, messages: List[Dict[str, Any]]) -> List[Triple]:
        """Extract all triples using message type-specific strategies."""
        logger.info(f"Starting Step 3 extraction on {len(messages)} messages")
        
        all_triples = []
        
        # Process messages by type
        for i, message in enumerate(messages):
            if i % 100 == 0:
                logger.info(f"Processing message {i+1}/{len(messages)}")
                
            msg_type = message.get('type', 'unknown')
            
            # Apply type-specific extraction
            if msg_type in self.extraction_strategies:
                strategy = self.extraction_strategies[msg_type]
                triples = strategy(message)
                all_triples.extend(triples)
            else:
                logger.debug(f"No extraction strategy for message type: {msg_type}")
        
        logger.info(f"Extracted {len(all_triples)} triples from message content")
        
        # Add Q&A linking
        qa_triples = self.qa_linker.link_qa_pairs(messages)
        all_triples.extend(qa_triples)
        
        logger.info(f"Total extraction complete: {len(all_triples)} triples from {len(messages)} messages")
        return all_triples
    
    def process_file(self, input_file: str, output_file: str) -> int:
        """Process a JSONL file and extract triples."""
        # Read messages
        messages = []
        with open(input_file, 'r') as f:
            for line in f:
                if line.strip():
                    messages.append(json.loads(line))
        
        logger.info(f"Loaded {len(messages)} messages from {input_file}")
        
        # Extract triples
        triples = self.extract_triples(messages)
        
        # Write output
        with open(output_file, 'w') as f:
            for triple in triples:
                f.write(json.dumps(triple.to_dict(), cls=NumpyEncoder) + '\n')
        
        logger.info(f"Wrote {len(triples)} triples to {output_file}")
        return len(triples)


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    extractor = Step3Extractor()
    
    # Command line usage
    if len(sys.argv) >= 3:
        input_file = sys.argv[1]
        output_file = sys.argv[2]
    else:
        # Default to preprocessing output
        input_candidates = [
            "../preprocessing/sample_results_5000.jsonl",
            "../preprocessing/sample_results.jsonl"
        ]
        
        input_file = None
        for candidate in input_candidates:
            if os.path.exists(candidate):
                input_file = candidate
                break
        
        if not input_file:
            print("Usage: python extractor.py <input_file> <output_file>")
            sys.exit(1)
            
        output_file = "step3_triples.jsonl"
    
    print(f"Step 3 Processing: {input_file} -> {output_file}")
    num_triples = extractor.process_file(input_file, output_file)
    print(f"✓ Extracted {num_triples} triples")
    print(f"✓ Results saved to: {output_file}")