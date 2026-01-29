"""VB Code Analyzer - Analyzes VB.NET custom code in reports."""

import logging
import re

from app.schemas.analysis import AnalysisFeatures, CustomCodeFunction
from app.schemas.code_analysis import (
    SPComplexity,
    VBFunctionAnalysis,
    VBPatternCategory,
)

logger = logging.getLogger(__name__)


class VBCodeAnalyzer:
    """Analyzes VB.NET custom code blocks in SSRS reports."""

    # Pattern detectors for common VB patterns
    PATTERN_DETECTORS: dict[VBPatternCategory, list[re.Pattern[str]]] = {
        VBPatternCategory.DATE_FORMATTING: [
            re.compile(r"Format\s*\([^,]+,\s*[\"'][dDmMyY]", re.IGNORECASE),
            re.compile(r"DateDiff\s*\(", re.IGNORECASE),
            re.compile(r"DateAdd\s*\(", re.IGNORECASE),
            re.compile(r"DatePart\s*\(", re.IGNORECASE),
            re.compile(r"DateSerial\s*\(", re.IGNORECASE),
            re.compile(r"Month\s*\(|Year\s*\(|Day\s*\(", re.IGNORECASE),
            re.compile(r"Now\s*\(?\s*\)?|Today\s*\(?\s*\)?", re.IGNORECASE),
        ],
        VBPatternCategory.STRING_MANIPULATION: [
            re.compile(r"Left\s*\(", re.IGNORECASE),
            re.compile(r"Right\s*\(", re.IGNORECASE),
            re.compile(r"Mid\s*\(", re.IGNORECASE),
            re.compile(r"Replace\s*\(", re.IGNORECASE),
            re.compile(r"Trim\s*\(|LTrim\s*\(|RTrim\s*\(", re.IGNORECASE),
            re.compile(r"UCase\s*\(|LCase\s*\(", re.IGNORECASE),
            re.compile(r"InStr\s*\(|InStrRev\s*\(", re.IGNORECASE),
            re.compile(r"Split\s*\(|Join\s*\(", re.IGNORECASE),
            re.compile(r"Len\s*\(", re.IGNORECASE),
            re.compile(r"String\.Format\s*\(", re.IGNORECASE),
        ],
        VBPatternCategory.MATH_OPERATIONS: [
            re.compile(r"Round\s*\(", re.IGNORECASE),
            re.compile(r"Abs\s*\(", re.IGNORECASE),
            re.compile(r"Int\s*\(|Fix\s*\(", re.IGNORECASE),
            re.compile(r"CDbl\s*\(|CInt\s*\(|CLng\s*\(|CDec\s*\(", re.IGNORECASE),
            re.compile(r"Math\.\w+\s*\(", re.IGNORECASE),
            re.compile(r"Mod\s+", re.IGNORECASE),
        ],
        VBPatternCategory.CONDITIONAL_LOGIC: [
            re.compile(r"IIf\s*\(", re.IGNORECASE),
            re.compile(r"Select\s+Case\b", re.IGNORECASE),
            re.compile(r"\bIf\s+.+\s+Then\b", re.IGNORECASE),
            re.compile(r"Choose\s*\(", re.IGNORECASE),
        ],
        VBPatternCategory.NULL_HANDLING: [
            re.compile(r"IsNothing\s*\(", re.IGNORECASE),
            re.compile(r"IsDBNull\s*\(", re.IGNORECASE),
            re.compile(r"\bNothing\b", re.IGNORECASE),
            re.compile(r"IsNull\s*\(", re.IGNORECASE),
            re.compile(r"NullIf\s*\(|Coalesce\s*\(", re.IGNORECASE),
        ],
        VBPatternCategory.ERROR_HANDLING: [
            re.compile(r"Try\s*\n", re.IGNORECASE),
            re.compile(r"Catch\s+", re.IGNORECASE),
            re.compile(r"On\s+Error\s+", re.IGNORECASE),
            re.compile(r"Throw\s+", re.IGNORECASE),
        ],
        VBPatternCategory.COLLECTION_OPERATIONS: [
            re.compile(r"For\s+Each\s+", re.IGNORECASE),
            re.compile(r"\.Count\b|\.Length\b", re.IGNORECASE),
            re.compile(r"\.Add\s*\(|\.Remove\s*\(", re.IGNORECASE),
            re.compile(r"Array\s*\(|ArrayList", re.IGNORECASE),
            re.compile(r"Dictionary", re.IGNORECASE),
        ],
    }

    # Function extraction regex
    FUNCTION_PATTERN = re.compile(
        r"(?:Public\s+|Private\s+)?(?:Shared\s+)?Function\s+(\w+)\s*\(([^)]*)\)"
        r"(.*?)End\s+Function",
        re.IGNORECASE | re.DOTALL,
    )

    # Sub extraction regex (VB procedures without return value)
    SUB_PATTERN = re.compile(
        r"(?:Public\s+|Private\s+)?(?:Shared\s+)?Sub\s+(\w+)\s*\(([^)]*)\)"
        r"(.*?)End\s+Sub",
        re.IGNORECASE | re.DOTALL,
    )

    def analyze_code_block(self, code: str | None) -> list[VBFunctionAnalysis]:
        """Parse VB code block and analyze each function.

        Args:
            code: The VB.NET code block content

        Returns:
            List of VBFunctionAnalysis for each function
        """
        if not code:
            return []

        functions = []

        # Extract functions
        for match in self.FUNCTION_PATTERN.finditer(code):
            name = match.group(1)
            params_str = match.group(2).strip()
            body = match.group(3).strip()

            functions.append(self._analyze_function(name, params_str, body))

        # Also check for Subs (procedures without return value)
        for match in self.SUB_PATTERN.finditer(code):
            name = match.group(1)
            params_str = match.group(2).strip()
            body = match.group(3).strip()

            func_analysis = self._analyze_function(name, params_str, body)
            functions.append(func_analysis)

        return functions

    def analyze_functions(
        self, custom_code_functions: list[CustomCodeFunction], custom_code: str | None
    ) -> list[VBFunctionAnalysis]:
        """Analyze VB functions from parsed features.

        Args:
            custom_code_functions: Pre-parsed function list
            custom_code: Raw code block for additional analysis

        Returns:
            List of VBFunctionAnalysis
        """
        # If we have the raw code, parse it for more detailed analysis
        if custom_code:
            return self.analyze_code_block(custom_code)

        # Otherwise, create analysis from pre-parsed functions
        results = []
        for func in custom_code_functions:
            results.append(
                VBFunctionAnalysis(
                    name=func.name,
                    parameters=func.parameters,
                    line_count=func.line_count,
                    patterns_detected=[],  # Can't detect patterns without code
                    complexity_estimate=self._estimate_complexity(
                        func.line_count, len(func.parameters), []
                    ),
                    conversion_difficulty=self._estimate_conversion_difficulty(
                        func.line_count, []
                    ),
                )
            )
        return results

    def analyze_features(self, features: AnalysisFeatures) -> list[VBFunctionAnalysis]:
        """Analyze VB code from analysis features.

        Args:
            features: Complete analysis features from RDL parsing

        Returns:
            List of VBFunctionAnalysis
        """
        return self.analyze_functions(
            features.custom_code_functions, features.custom_code
        )

    def _analyze_function(
        self, name: str, params_str: str, body: str
    ) -> VBFunctionAnalysis:
        """Analyze a single VB function.

        Args:
            name: Function name
            params_str: Parameter string
            body: Function body

        Returns:
            VBFunctionAnalysis
        """
        # Parse parameters
        parameters = self._parse_parameters(params_str)

        # Count lines (non-empty, non-comment)
        lines = [
            line
            for line in body.split("\n")
            if line.strip() and not line.strip().startswith("'")
        ]
        line_count = len(lines)

        # Detect patterns
        patterns = self._detect_patterns(body)

        # Estimate complexity
        complexity = self._estimate_complexity(line_count, len(parameters), patterns)

        # Estimate conversion difficulty
        difficulty = self._estimate_conversion_difficulty(line_count, patterns)

        # Create body preview
        body_preview = body[:200].strip()
        if len(body) > 200:
            body_preview += "..."

        return VBFunctionAnalysis(
            name=name,
            parameters=parameters,
            line_count=line_count,
            patterns_detected=patterns,
            complexity_estimate=complexity,
            body_preview=body_preview,
            conversion_difficulty=difficulty,
        )

    def _parse_parameters(self, params_str: str) -> list[str]:
        """Parse VB parameter string into list.

        Args:
            params_str: VB parameter declaration string

        Returns:
            List of parameter names
        """
        if not params_str.strip():
            return []

        params = []
        for param in params_str.split(","):
            param = param.strip()
            if not param:
                continue

            # Extract parameter name (handle ByVal/ByRef, type declarations)
            # Format: [ByVal|ByRef] name [As Type]
            match = re.match(
                r"(?:ByVal\s+|ByRef\s+)?(\w+)(?:\s+As\s+\w+)?",
                param,
                re.IGNORECASE,
            )
            if match:
                params.append(match.group(1))
            else:
                # Fallback: just take the first word
                parts = param.split()
                if parts:
                    params.append(parts[-1].split()[0])

        return params

    def _detect_patterns(self, code: str) -> list[VBPatternCategory]:
        """Detect common patterns in VB code.

        Args:
            code: VB code content

        Returns:
            List of detected pattern categories
        """
        detected = []
        for category, patterns in self.PATTERN_DETECTORS.items():
            for pattern in patterns:
                if pattern.search(code):
                    detected.append(category)
                    break  # Only add category once
        return detected

    def _estimate_complexity(
        self, line_count: int, param_count: int, patterns: list[VBPatternCategory]
    ) -> SPComplexity:
        """Estimate function complexity.

        Args:
            line_count: Number of lines of code
            param_count: Number of parameters
            patterns: Detected patterns

        Returns:
            Complexity estimate
        """
        score = 0

        # Line count contribution
        if line_count <= 5:
            score += 0
        elif line_count <= 15:
            score += 1
        elif line_count <= 30:
            score += 2
        else:
            score += 3

        # Parameter count contribution
        if param_count <= 2:
            score += 0
        elif param_count <= 4:
            score += 1
        else:
            score += 2

        # Pattern complexity contribution
        complex_patterns = {
            VBPatternCategory.ERROR_HANDLING,
            VBPatternCategory.COLLECTION_OPERATIONS,
        }
        if any(p in complex_patterns for p in patterns):
            score += 1

        # Determine complexity
        if score <= 1:
            return SPComplexity.SIMPLE
        elif score <= 3:
            return SPComplexity.MODERATE
        else:
            return SPComplexity.COMPLEX

    def _estimate_conversion_difficulty(
        self, line_count: int, patterns: list[VBPatternCategory]
    ) -> str:
        """Estimate conversion difficulty.

        Args:
            line_count: Number of lines of code
            patterns: Detected patterns

        Returns:
            "low", "medium", or "high"
        """
        # High difficulty patterns
        high_difficulty = {
            VBPatternCategory.ERROR_HANDLING,
            VBPatternCategory.COLLECTION_OPERATIONS,
        }

        # Medium difficulty patterns
        medium_difficulty = {
            VBPatternCategory.CONDITIONAL_LOGIC,
            VBPatternCategory.NULL_HANDLING,
        }

        if any(p in high_difficulty for p in patterns) or line_count > 30:
            return "high"
        elif any(p in medium_difficulty for p in patterns) or line_count > 15:
            return "medium"
        else:
            return "low"


def analyze_vb_code(features: AnalysisFeatures) -> list[VBFunctionAnalysis]:
    """Convenience function to analyze VB code.

    Args:
        features: Analysis features from RDL parsing

    Returns:
        List of VBFunctionAnalysis
    """
    analyzer = VBCodeAnalyzer()
    return analyzer.analyze_features(features)
