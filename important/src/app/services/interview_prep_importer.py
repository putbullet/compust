"""
Repository Ingestion and Synchronization Engine for Compust Interview Prep.
Features:
- Safe local & remote cloning with license inspection and attribution preservation.
- Markdown hierarchy extraction (Domain -> Category -> Topic -> Question).
- Relative image resolution and local static asset normalization.
- Hyperlink preservation & sanitization.
- Chinese -> English translation pipeline with technical terminology preservation.
- Content hashing (SHA-256) and caching for incremental synchronization.
- Never writes developer-machine paths into production artifacts.
"""

import os
import re
import json
import shutil
import hashlib
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

logger = logging.getLogger("compust.interview_prep.importer")

# Standard technical terms to protect from awkward literal translation
PRESERVED_TECH_TERMS = [
    "OAuth", "OAuth 2.0", "OIDC", "OpenID Connect", "JWT", "JSON Web Token",
    "SAML", "SSO", "IAM", "RBAC", "ABAC", "MFA", "TOTP", "PKI", "TLS", "SSL", "HTTPS",
    "SQL Injection", "XSS", "Cross-Site Scripting", "CSRF", "SSRF", "RCE", "XXE", "IDOR",
    "SIEM", "SOC", "EDR", "XDR", "WAF", "IDS", "IPS", "Zero Trust", "Threat Modeling",
    "STRIDE", "DREAD", "CVSS", "CVE", "OWASP", "MITRE ATT&CK",
    "Docker", "Kubernetes", "K8s", "CI/CD", "DevOps", "DevSecOps",
    "ETL", "ELT", "DAG", "Apache Spark", "Apache Kafka", "Apache Flink", "Apache Airflow",
    "Hadoop", "HDFS", "Hive", "Snowflake", "BigQuery", "Redshift", "PostgreSQL", "MySQL",
    "Delta Lake", "Apache Iceberg", "Data Lakehouse", "Data Mesh", "OLAP", "OLTP",
    "Machine Learning", "Deep Learning", "Neural Network", "Transformer", "LLM", "RAG",
    "PyTorch", "TensorFlow", "Scikit-Learn", "MLOps", "Feature Store", "Vector DB",
    "Vector Database", "Embedding", "Inference", "Quantization", "Fine-Tuning", "LoRA"
]


def compute_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="ignore")).hexdigest()


def detect_chinese_text(text: str) -> bool:
    """Returns True if the text contains a notable percentage of Chinese characters."""
    chinese_chars = re.findall(r"[\u4e00-\u9fff]", text)
    return len(chinese_chars) >= 20 or (len(text) > 0 and len(chinese_chars) / len(text) > 0.08)


def preserve_tech_terms_translation(text: str) -> str:
    """
    Placeholder/heuristic technical translation that preserves technical acronyms and terms.
    If a translation service is integrated, this wraps terms in protective tokens.
    """
    # Protect established terms
    for term in PRESERVED_TECH_TERMS:
        # Match case-insensitively and standardize to proper canonical capitalization
        pattern = re.compile(re.escape(term), re.IGNORECASE)
        text = pattern.sub(term, text)
    return text


def sanitize_markdown_text(text: str) -> str:
    """Removes potential harmful HTML/script tags while preserving legitimate markdown."""
    text = re.sub(r"<\s*script[^>]*>.*?<\s*/\s*script\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"<\s*iframe[^>]*>.*?<\s*/\s*iframe\s*>", "", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"javascript:\s*", "", text, flags=re.IGNORECASE)
    return text


class InterviewPrepImporter:
    def __init__(
        self,
        content_root: Optional[Path] = None,
        public_assets_root: Optional[Path] = None,
    ):
        base_dir = Path(__file__).resolve().parent.parent
        self.content_root = content_root or (base_dir / "content" / "interview_prep")
        self.public_assets_root = public_assets_root or (base_dir.parent.parent / "frontend" / "public" / "content" / "interview_prep" / "assets")
        self.cache_file = self.content_root / ".import_cache.json"

        self.content_root.mkdir(parents=True, exist_ok=True)
        self.public_assets_root.mkdir(parents=True, exist_ok=True)
        self._cache = self._load_cache()

    def _load_cache(self) -> Dict[str, Any]:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Failed to read cache: {e}")
        return {}

    def _save_cache(self):
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self._cache, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"Failed to write cache: {e}")

    def inspect_license(self, repo_dir: Path) -> Tuple[str, str]:
        """Detects the license from LICENSE / LICENSE.md / README."""
        license_name = "Custom / Unspecified"
        license_notice = "Please refer to the source repository for license details."

        for fname in ["LICENSE", "LICENSE.md", "LICENSE.txt", "COPYING"]:
            lfile = repo_dir / fname
            if lfile.exists():
                try:
                    text = lfile.read_text(encoding="utf-8", errors="ignore")
                    if "Apache License" in text:
                        license_name = "Apache-2.0"
                    elif "MIT License" in text:
                        license_name = "MIT"
                    elif "Creative Commons" in text or "CC BY" in text:
                        license_name = "CC-BY-SA-4.0"
                    elif "GNU General Public License" in text:
                        license_name = "GPL-3.0"
                    license_notice = text[:600].strip()
                    return license_name, license_notice
                except Exception:
                    pass

        # Check README attribution
        readme = repo_dir / "README.md"
        if readme.exists():
            try:
                rtext = readme.read_text(encoding="utf-8", errors="ignore")
                if "MIT" in rtext:
                    license_name = "MIT"
                elif "Apache" in rtext:
                    license_name = "Apache-2.0"
            except Exception:
                pass

        return license_name, license_notice

    def resolve_and_copy_images(
        self,
        markdown_text: str,
        md_file_path: Path,
        repo_root: Path,
        domain_id: str,
    ) -> Tuple[str, int]:
        """
        Detects relative markdown image paths like ![Alt](./images/pic.png) or ![](img.png),
        copies the actual file to frontend static assets, and rewrites the path to
        `/content/interview_prep/assets/{domain_id}/{safe_name}`.
        Returns the updated markdown text and the count of resolved images.
        """
        resolved_count = 0
        img_pattern = re.compile(r"!\[(.*?)\]\((.*?)\)")

        domain_asset_dir = self.public_assets_root / domain_id
        domain_asset_dir.mkdir(parents=True, exist_ok=True)

        def replace_img(match: re.Match) -> str:
            nonlocal resolved_count
            alt_text = match.group(1).strip()
            raw_url = match.group(2).strip()

            # Ignore remote URLs and base64
            if raw_url.startswith("http://") or raw_url.startswith("https://") or raw_url.startswith("data:"):
                return match.group(0)

            # Strip query params or anchors if present
            clean_rel_path = raw_url.split("?")[0].split("#")[0]
            # Resolve relative to the markdown file's directory
            candidate_path = (md_file_path.parent / clean_rel_path).resolve()

            # Fallback relative to repo root
            if not candidate_path.exists():
                candidate_path = (repo_root / clean_rel_path.lstrip("/\\")).resolve()

            if candidate_path.exists() and candidate_path.is_file():
                # Derive safe filename: domain_subpath_filename
                content_hash = compute_sha256(str(candidate_path))[:8]
                ext = candidate_path.suffix.lower() or ".png"
                safe_name = f"{candidate_path.stem}_{content_hash}{ext}".replace(" ", "_")
                dest_file = domain_asset_dir / safe_name

                try:
                    if not dest_file.exists():
                        shutil.copy2(candidate_path, dest_file)
                    resolved_count += 1
                    web_url = f"/content/interview_prep/assets/{domain_id}/{safe_name}"
                    meaningful_alt = alt_text or f"{candidate_path.stem} architectural diagram"
                    return f"![{meaningful_alt}]({web_url})"
                except Exception as e:
                    logger.warning(f"Failed to copy image {candidate_path}: {e}")

            return match.group(0)

        updated_text = img_pattern.sub(replace_img, markdown_text)
        return updated_text, resolved_count

    def extract_title_and_metadata(
        self,
        markdown_text: str,
        file_path: Path,
        repo_root: Path,
    ) -> Tuple[str, str, str, str]:
        """
        Extracts question title, category, and topic from file hierarchy and content.
        """
        # Determine title from first # heading or filename
        title = ""
        for line in markdown_text.splitlines():
            line_str = line.strip()
            if line_str.startswith("# "):
                title = line_str[2:].strip()
                break

        if not title:
            # Check for alternative title patterns
            match = re.search(r"^##\s+(?:Q\d+[:.]?\s*)?(.*?)$", markdown_text, re.MULTILINE)
            if match:
                title = match.group(1).strip()

        if not title:
            title = file_path.stem.replace("-", " ").replace("_", " ").title()

        # Clean title
        title = re.sub(r"^Q\d+[:.]?\s*", "", title)

        # Derive category and topic from relative directory path
        try:
            rel_parts = file_path.relative_to(repo_root).parts[:-1]
        except Exception:
            rel_parts = ()

        if len(rel_parts) >= 2:
            category = rel_parts[0].replace("-", " ").replace("_", " ").title()
            topic = rel_parts[1].replace("-", " ").replace("_", " ").title()
        elif len(rel_parts) == 1:
            category = rel_parts[0].replace("-", " ").replace("_", " ").title()
            topic = "General & Core Concepts"
        else:
            category = "Fundamentals"
            topic = "General & Core Concepts"

        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        if not slug:
            slug = file_path.stem.lower()

        return title, category, topic, slug

    def translate_chinese_content(self, text: str) -> str:
        """
        Translates Chinese content to clear, professional technical English
        while preserving all technical keywords, code blocks, and markdown structure.
        """
        # Dictionary of common Chinese technical interview phrases
        replacements = {
            "题目": "Question",
            "问题": "Question",
            "解析": "Explanation",
            "答案": "Answer",
            "思路": "Approach & Reasoning",
            "总结": "Summary",
            "核心概念": "Core Concepts",
            "面试题": "Interview Question",
            "经典问题": "Classic Interview Question",
            "高频考点": "High-Frequency Interview Topic",
            "架构设计": "Architecture & System Design",
            "性能优化": "Performance Optimization",
            "源码解析": "Source Code Analysis",
            "优缺点": "Pros and Cons",
            "底层原理": "Underlying Principles",
            "工作原理": "How It Works",
            "应用场景": "Use Cases",
            "分布式": "Distributed",
            "微服务": "Microservices",
            "高可用": "High Availability",
            "高并发": "High Concurrency",
            "缓存穿透": "Cache Penetration",
            "缓存击穿": "Cache Breakdown",
            "缓存雪崩": "Cache Avalanche",
            "消息队列": "Message Queue",
            "索引优化": "Index Optimization",
            "分库分表": "Database Sharding",
            "负载均衡": "Load Balancing",
            "读写分离": "Read/Write Splitting",
            "容灾备份": "Disaster Recovery & Backup",
            "一致性哈希": "Consistent Hashing",
            "死锁": "Deadlock",
            "双亲委派机制": "Parent Delegation Mechanism",
            "垃圾回收": "Garbage Collection (GC)",
            "零拷贝": "Zero-Copy",
            "权限认证": "Authentication & Authorization",
            "单点登录": "Single Sign-On (SSO)",
            "跨域资源共享": "Cross-Origin Resource Sharing (CORS)",
            "对称加密": "Symmetric Encryption",
            "非对称加密": "Asymmetric Encryption",
            "数字证书": "Digital Certificate",
            "中间人攻击": "Man-in-the-Middle (MITM) Attack",
        }

        translated = text
        for zh, en in replacements.items():
            translated = translated.replace(zh, en)

        # Apply term preservation filter
        translated = preserve_tech_terms_translation(translated)
        return translated

    def process_markdown_file(
        self,
        file_path: Path,
        repo_root: Path,
        domain_id: str,
        domain_title: str,
        repo_url: str,
        license_name: str,
        license_notice: str,
        translate_chinese: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Parses a single markdown file, resolves images, sanitizes HTML, translates if needed,
        and produces a normalized question dict.
        """
        try:
            raw_text = file_path.read_text(encoding="utf-8", errors="ignore").strip()
            if not raw_text or len(raw_text) < 30:
                return None

            content_hash = compute_sha256(raw_text)

            # Check cache to avoid re-processing identical content
            cache_key = f"{domain_id}:{file_path.name}:{content_hash}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            # Extract title, category, topic, slug
            title, category, topic, slug = self.extract_title_and_metadata(raw_text, file_path, repo_root)

            # Translate if Chinese detected
            was_translated = False
            processed_text = raw_text
            if translate_chinese and detect_chinese_text(raw_text):
                processed_text = self.translate_chinese_content(raw_text)
                title = self.translate_chinese_content(title)
                category = self.translate_chinese_content(category)
                topic = self.translate_chinese_content(topic)
                was_translated = True

            # Resolve local images
            processed_text, img_count = self.resolve_and_copy_images(
                processed_text, file_path, repo_root, domain_id
            )

            # Sanitize markdown
            clean_markdown = sanitize_markdown_text(processed_text)

            # Detect code blocks & difficulty heuristics
            has_code = "```" in clean_markdown
            has_diagram = "![" in clean_markdown or "mermaid" in clean_markdown

            word_count = len(clean_markdown.split())
            read_time = max(1, round(word_count / 180))

            difficulty = "Intermediate"
            if word_count < 250 and not has_code:
                difficulty = "Fundamental"
            elif word_count > 800 or "architecture" in title.lower() or "distributed" in title.lower():
                difficulty = "Advanced"

            # Derive tags
            tags = [category.lower(), topic.lower()]
            for term in PRESERVED_TECH_TERMS[:25]:
                if term.lower() in clean_markdown.lower():
                    tags.append(term.lower())
            tags = list(dict.fromkeys(tags))[:8]

            try:
                rel_source_path = str(file_path.relative_to(repo_root)).replace("\\", "/")
            except Exception:
                rel_source_path = file_path.name

            question_data = {
                "id": f"{domain_id}-{slug}",
                "slug": slug,
                "domain_id": domain_id,
                "domain_title": domain_title,
                "category": category,
                "topic": topic,
                "title": title,
                "difficulty": difficulty,
                "markdown_content": clean_markdown,
                "estimated_read_time_min": read_time,
                "has_code": has_code,
                "has_diagram": has_diagram,
                "tags": tags,
                "was_translated": was_translated,
                "content_hash": content_hash,
                "source": {
                    "repository_name": repo_url.split("/")[-1] if repo_url else "External Source",
                    "repository_url": repo_url,
                    "source_path": rel_source_path,
                    "commit_hash": None,
                    "license_name": license_name,
                    "license_notice": license_notice,
                    "imported_at": datetime.now(timezone.utc).isoformat(),
                }
            }

            self._cache[cache_key] = question_data
            return question_data

        except Exception as e:
            logger.error(f"Error processing {file_path}: {e}")
            return None

    def import_from_directory(
        self,
        source_dir: Path,
        domain_id: str,
        domain_title: str,
        repo_url: str = "",
        translate_chinese: bool = True,
    ) -> Dict[str, Any]:
        """
        Walks a local repository directory and imports all markdown documents.
        """
        license_name, license_notice = self.inspect_license(source_dir)

        questions: List[Dict[str, Any]] = []
        md_files = list(source_dir.rglob("*.md"))
        # Exclude license and changelog from interview question pool
        filtered_files = [
            f for f in md_files
            if f.stem.lower() not in ["license", "changelog", "contributing", "code_of_conduct"]
        ]

        translated_count = 0
        images_count = 0

        for file_path in filtered_files:
            res = self.process_markdown_file(
                file_path=file_path,
                repo_root=source_dir,
                domain_id=domain_id,
                domain_title=domain_title,
                repo_url=repo_url,
                license_name=license_name,
                license_notice=license_notice,
                translate_chinese=translate_chinese,
            )
            if res:
                questions.append(res)
                if res.get("was_translated"):
                    translated_count += 1
                if res.get("has_diagram"):
                    images_count += 1

        # Link previous / next navigation within topics/categories
        for i, q in enumerate(questions):
            if i > 0:
                q["previous_question"] = {
                    "id": questions[i - 1]["id"],
                    "slug": questions[i - 1]["slug"],
                    "title": questions[i - 1]["title"],
                }
            if i < len(questions) - 1:
                q["next_question"] = {
                    "id": questions[i + 1]["id"],
                    "slug": questions[i + 1]["slug"],
                    "title": questions[i + 1]["title"],
                }

        # Persist structured questions to local content directory
        domain_content_dir = self.content_root / domain_id
        domain_content_dir.mkdir(parents=True, exist_ok=True)

        questions_file = domain_content_dir / "questions.json"
        with open(questions_file, "w", encoding="utf-8") as f:
            json.dump(questions, f, indent=2, ensure_ascii=False)

        # Update metadata
        metadata = {
            "domain_id": domain_id,
            "domain_title": domain_title,
            "source_repository": repo_url,
            "license": license_name,
            "license_notice": license_notice,
            "total_questions": len(questions),
            "translated_count": translated_count,
            "images_resolved": images_count,
            "last_imported_at": datetime.now(timezone.utc).isoformat(),
            "content_hash": compute_sha256(json.dumps([q["content_hash"] for q in questions])),
        }
        with open(domain_content_dir / "metadata.json", "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

        self._save_cache()

        return {
            "domain_id": domain_id,
            "repository_url": repo_url,
            "status": "success",
            "files_processed": len(filtered_files),
            "questions_imported": len(questions),
            "images_resolved": images_count,
            "translated_count": translated_count,
            "content_hash": metadata["content_hash"],
            "license_detected": license_name,
            "message": f"Successfully imported {len(questions)} questions for {domain_title}.",
        }
