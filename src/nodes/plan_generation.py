"""Enhanced node classes for the Plan Generation Flow."""

from pocketflow import Node

from domain.config import (
    PlanValidationResult,
    ResearchPlan,
    UserPlanningInput,
)
from domain.shared_store import (
    get_shared_store,
    update_shared_store,
)
from utils.llm_utils import call_llm_structured

# =====================================================================
# PLANNING FLOW NODES
# =====================================================================


class UserPlanningConfigNode(Node):
    """Interactive node to gather user planning preferences and configuration."""

    def prep(self, shared):
        """Read research idea, novelty assessment, and top papers for context."""
        store = get_shared_store(shared)
        return (
            store.final_ideas,
            store.novelty_assessment,
            store.final_papers[:5] if store.final_papers else [],
        )

    def exec(self, prep_res):
        """Interactive gathering of user planning preferences."""
        research_idea, novelty_assessment, top_papers = prep_res

        # Display context to user
        print("\n" + "=" * 60)
        print("🎯 RESEARCH PLANNING CONFIGURATION")
        print("=" * 60)
        print(
            f"📋 Research Idea: {research_idea[:200]}..."
            if research_idea
            else "No research idea available"
        )

        if novelty_assessment:
            print(f"🔍 Novelty Score: {novelty_assessment.final_novelty_score:.2f}/1.0")
            print(f"📊 Confidence: {novelty_assessment.confidence:.2f}")

        if top_papers:
            print(f"📚 Similar Papers Found: {len(top_papers)} papers analyzed")

        print("\n" + "-" * 60)

        # Get project type
        print("📝 PROJECT TYPE SELECTION:")
        project_types = [
            (
                "academic_paper",
                "Academic Paper - Research paper for journal/conference",
            ),
            ("general_research", "General Research - Exploratory research project"),
            ("presentation", "Presentation - Conference talk or seminar"),
            (
                "educational_deepdive",
                "Educational Deep-dive - Comprehensive learning material",
            ),
            (
                "technical_report",
                "Technical Report - Industry or organizational report",
            ),
            ("blog_post", "Blog Post - Public-facing article or blog content"),
        ]

        for i, (key, description) in enumerate(project_types, 1):
            print(f"{i}. {description}")

        while True:
            try:
                choice = input(
                    f"\nSelect project type (1-{len(project_types)}): "
                ).strip()
                if choice.isdigit() and 1 <= int(choice) <= len(project_types):
                    selected_type = project_types[int(choice) - 1][0]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(project_types)}")
            except ValueError:
                print("Please enter a valid number")

        # Get timeline
        print("\n⏰ TIMELINE SELECTION:")
        timeline_options = [
            ("1_week", "1 Week - Quick turnaround project"),
            ("2_weeks", "2 Weeks - Short-term focused effort"),
            ("1_month", "1 Month - Standard project timeline"),
            ("3_months", "3 Months - Comprehensive research project"),
            ("6_months", "6 Months - Extended research initiative"),
            ("1_year", "1 Year - Long-term research program"),
        ]

        for i, (key, description) in enumerate(timeline_options, 1):
            print(f"{i}. {description}")

        while True:
            try:
                choice = input(
                    f"\nSelect timeline (1-{len(timeline_options)}): "
                ).strip()
                if choice.isdigit() and 1 <= int(choice) <= len(timeline_options):
                    selected_timeline = timeline_options[int(choice) - 1][0]
                    break
                else:
                    print(
                        f"Please enter a number between 1 and {len(timeline_options)}"
                    )
            except ValueError:
                print("Please enter a valid number")

        # Get additional requirements
        print("\n💭 ADDITIONAL REQUIREMENTS:")
        additional_requirements = input(
            "Any specific requirements or constraints? (press Enter to skip): "
        ).strip()

        # Get target audience
        print("\n👥 TARGET AUDIENCE:")
        audiences = [
            ("academic", "Academic - Researchers, professors, graduate students"),
            ("industry", "Industry - Professional practitioners, engineers"),
            ("general", "General Public - Accessible to broad audience"),
            ("educational", "Educational - Students, learners at various levels"),
        ]

        for i, (key, description) in enumerate(audiences, 1):
            print(f"{i}. {description}")

        while True:
            try:
                choice = input(
                    f"\nSelect target audience (1-{len(audiences)}): "
                ).strip()
                if choice.isdigit() and 1 <= int(choice) <= len(audiences):
                    selected_audience = audiences[int(choice) - 1][0]
                    break
                else:
                    print(f"Please enter a number between 1 and {len(audiences)}")
            except ValueError:
                print("Please enter a valid number")

        # Get resources available
        resources_available = input(
            "\n🔧 Available resources (budget, team size, tools, etc.) - optional: "
        ).strip()

        # Create UserPlanningInput object
        user_input = UserPlanningInput(
            project_type=selected_type,
            timeline=selected_timeline,
            additional_requirements=additional_requirements,
            target_audience=selected_audience,
            resources_available=resources_available,
        )

        print("\n✅ Planning configuration completed!")
        return user_input

    def post(self, shared, prep_res, exec_res):
        """Store user planning input in shared store."""
        store = get_shared_store(shared)
        store.user_planning_input = exec_res
        update_shared_store(shared, store)

        print(
            f"📝 Configuration saved: {exec_res.project_type} project, {exec_res.timeline} timeline"
        )
        return "default"


class PlanGenerationNode(Node):
    """Generate comprehensive research plan using LLM with structured output."""

    def prep(self, shared):
        """Read all necessary data for plan generation."""
        store = get_shared_store(shared)

        # Include user feedback from validation history if available
        user_feedback = None
        refinement_areas = []
        if store.plan_validation_history:
            latest_validation = store.plan_validation_history[-1]
            if latest_validation.refinement_suggestions:
                user_feedback = latest_validation.refinement_suggestions
            if latest_validation.areas_to_improve:
                refinement_areas = latest_validation.areas_to_improve

        return (
            store.final_ideas,
            store.novelty_assessment,
            store.final_papers[:10] if store.final_papers else [],
            store.user_planning_input,
            user_feedback,
            refinement_areas,
        )

    def exec(self, prep_res):
        """Generate structured research plan using LLM."""
        (
            research_idea,
            novelty_assessment,
            top_papers,
            user_config,
            feedback,
            refinement_areas,
        ) = prep_res

        # Build comprehensive planning prompt
        prompt = self._build_planning_prompt(
            research_idea,
            novelty_assessment,
            top_papers,
            user_config,
            feedback,
            refinement_areas,
        )

        # Generate plan using structured output
        research_plan = call_llm_structured(
            prompt=prompt,
            response_model=ResearchPlan,
            instructions="Generate a comprehensive, actionable research plan with detailed phases and realistic timelines.",
        )

        return research_plan

    def _build_planning_prompt(
        self,
        research_idea,
        novelty_assessment,
        papers,
        config,
        feedback,
        refinement_areas,
    ):
        """Build comprehensive prompt for research plan generation."""

        # Base context
        prompt = f"""
        You are an expert research planning consultant. Generate a comprehensive, actionable research plan based on the following information.

        RESEARCH IDEA TO PLAN FOR:
        {research_idea}

        PROJECT CONFIGURATION:
        - Project Type: {config.project_type}
        - Timeline: {config.timeline}
        - Target Audience: {config.target_audience}
        - Additional Requirements: {config.additional_requirements}
        - Available Resources: {config.resources_available}
        """

        # Add novelty context if available
        if novelty_assessment:
            prompt += f"""

            NOVELTY ASSESSMENT:
            - Overall Novelty Score: {novelty_assessment.final_novelty_score:.2f}/1.0
            - Confidence: {novelty_assessment.confidence:.2f}
            - Papers Analyzed: {novelty_assessment.final_papers_count}
            - Assessment Summary: {novelty_assessment.assessment_summary[:300]}...
            """

        # Add similar papers context
        if papers:
            prompt += f"""

            SIMILAR EXISTING RESEARCH (Top {len(papers)} papers):
            """
            for i, paper in enumerate(papers[:5], 1):
                prompt += (
                    f"{i}. {paper.paper.title} (novelty: {paper.novelty_score:.3f})\n"
                )

        # Add feedback if this is a refinement
        if feedback:
            prompt += f"""

            USER FEEDBACK FOR REFINEMENT:
            {feedback}
            """

        if refinement_areas:
            prompt += f"""

            SPECIFIC AREAS TO IMPROVE:
            {", ".join(refinement_areas)}
            """

        # Add planning instructions based on project type
        project_instructions = {
            "academic_paper": "Focus on literature review, methodology, experiments, and publication timeline",
            "general_research": "Emphasize exploration, hypothesis formation, and knowledge discovery",
            "presentation": "Structure for compelling storytelling, visual design, and audience engagement",
            "educational_deepdive": "Create learning progression, knowledge building, and comprehension checks",
            "technical_report": "Emphasize practical implementation, testing, and deliverable documentation",
            "blog_post": "Focus on accessible writing, audience engagement, and content distribution",
        }

        timeline_guidance = {
            "1_week": "Create an intensive, focused plan with daily milestones",
            "2_weeks": "Structure with 3-4 major phases and weekly checkpoints",
            "1_month": "Develop 4-5 phases with weekly milestones and buffer time",
            "3_months": "Create comprehensive phases with monthly major milestones",
            "6_months": "Design extensive phases with bi-monthly reviews and pivots",
            "1_year": "Structure with quarterly phases and seasonal planning cycles",
        }

        prompt += f"""

        PLANNING REQUIREMENTS:
        1. Create a research plan specifically tailored for: {project_instructions.get(config.project_type, "general research project")}
        2. Timeline considerations: {timeline_guidance.get(config.timeline, "appropriate phase distribution")}
        3. Consider the novelty assessment when planning literature review and positioning
        4. Include specific, measurable deliverables for each phase
        5. Account for potential challenges and mitigation strategies
        6. Ensure the plan is actionable with clear next steps

        PLAN STRUCTURE REQUIREMENTS:
        - Create 3-6 phases depending on timeline
        - Each phase should have specific tasks, deliverables, and milestones  
        - Include resource requirements and potential challenges
        - Define clear success metrics
        - Reference relevant papers from the similar research
        - Tailor language and depth to the target audience

        Generate a comprehensive plan that balances ambition with practicality.
        """

        return prompt

    def post(self, shared, prep_res, exec_res):
        """Store generated research plan in shared store."""
        store = get_shared_store(shared)
        store.research_plan = exec_res
        update_shared_store(shared, store)

        print(f"📋 Research plan generated: {exec_res.title}")
        print(
            f"📅 {len(exec_res.phases)} phases planned for {exec_res.timeline} timeline"
        )
        return "default"


class PlanValidationNode(Node):
    """Interactive validation of generated research plan with user feedback."""

    def prep(self, shared):
        """Read current plan, validation history, and configuration."""
        store = get_shared_store(shared)
        return store.research_plan, store.plan_validation_history, store.plan_config

    def exec(self, prep_res):
        """Present plan to user and gather validation feedback."""
        plan, validation_history, config = prep_res

        current_cycle = len(validation_history) + 1

        # Display the plan in a beautiful format
        print("\n" + "=" * 80)
        print(
            f"📋 RESEARCH PLAN REVIEW - Cycle {current_cycle}/{config.max_refinement_cycles}"
        )
        print("=" * 80)

        self._display_plan_summary(plan)

        # Get user validation
        print("\n" + "=" * 80)
        print("🔍 PLAN VALIDATION")
        print("=" * 80)

        # Ask for approval
        while True:
            approval = (
                input("\n✅ Do you approve this research plan? (y/n): ").strip().lower()
            )
            if approval in ["y", "yes"]:
                approved = True
                break
            elif approval in ["n", "no"]:
                approved = False
                break
            else:
                print("Please enter 'y' for yes or 'n' for no")

        # Get feedback
        if approved:
            feedback = "Plan approved by user"
            refinement_suggestions = ""
            areas_to_improve = []
        else:
            print("\n📝 Please provide feedback on what needs to be improved:")
            feedback = input("General feedback: ").strip()

            print("\n🎯 Specific areas to improve (optional):")
            print(
                "Common areas: timeline, phases, tasks, resources, challenges, success_metrics"
            )
            areas_input = input("Areas to improve (comma-separated): ").strip()
            areas_to_improve = [
                area.strip() for area in areas_input.split(",") if area.strip()
            ]

            refinement_suggestions = input("Specific refinement suggestions: ").strip()

        # Create validation result
        validation_result = PlanValidationResult(
            approved=approved,
            feedback=feedback,
            refinement_suggestions=refinement_suggestions,
            cycle_number=current_cycle,
            areas_to_improve=areas_to_improve,
        )

        return validation_result

    def _display_plan_summary(self, plan):
        """Display research plan in a beautiful, readable format."""
        print(f"\n🎯 {plan.title}")
        print(f"📊 Project Type: {plan.project_type.replace('_', ' ').title()}")
        print(f"⏰ Timeline: {plan.timeline.replace('_', ' ').title()}")
        print(f"👥 Target Audience: {plan.target_audience.title()}")

        print("\n📋 EXECUTIVE SUMMARY:")
        print(f"{plan.executive_summary}")

        print(f"\n📈 PLANNED PHASES ({len(plan.phases)} phases):")
        for phase in plan.phases:
            print(f"\n  Phase {phase.phase_number}: {phase.title}")
            print(f"  ⏱️  Duration: {phase.duration}")
            print(f"  📝 Description: {phase.description}")
            print(f"  ✅ Key Tasks: {len(phase.tasks)} tasks planned")
            print(f"  🎯 Deliverables: {len(phase.deliverables)} deliverables")

        if plan.resources_needed:
            print("\n🔧 RESOURCES NEEDED:")
            for resource in plan.resources_needed[:5]:  # Show first 5
                print(f"  • {resource}")

        if plan.potential_challenges:
            print("\n⚠️  POTENTIAL CHALLENGES:")
            for challenge in plan.potential_challenges[:3]:  # Show first 3
                print(f"  • {challenge}")

        if plan.success_metrics:
            print("\n📊 SUCCESS METRICS:")
            for metric in plan.success_metrics[:3]:  # Show first 3
                print(f"  • {metric}")

    def post(self, shared, prep_res, exec_res):
        """Update validation history and determine next action."""
        store = get_shared_store(shared)
        store.plan_validation_history.append(exec_res)
        store.plan_current_cycle += 1
        update_shared_store(shared, store)

        print(f"\n📝 Validation cycle {exec_res.cycle_number} completed")

        # Determine flow control
        if exec_res.approved:
            print("✅ Plan approved! Moving to finalization...")
            return "approve"
        elif store.plan_current_cycle >= store.plan_config.max_refinement_cycles:
            print(
                f"⏱️  Maximum refinement cycles ({store.plan_config.max_refinement_cycles}) reached. Moving to finalization..."
            )
            return "max_cycles_reached"
        else:
            print(
                f"🔄 Refining plan based on feedback... (Cycle {store.plan_current_cycle}/{store.plan_config.max_refinement_cycles})"
            )
            return "refine"


class PlanFinalizationNode(Node):
    """Finalize the research plan and prepare for output."""

    def prep(self, shared):
        """Read final plan and add completion metadata."""
        store = get_shared_store(shared)
        return store.research_plan, store.plan_validation_history

    def exec(self, prep_res):
        """Add final touches and metadata to the plan."""
        plan, validation_history = prep_res

        # Add validation metadata to plan
        if validation_history:
            final_validation = validation_history[-1]
            if final_validation.approved:
                plan.novelty_context += f"\n\nPlan approved after {len(validation_history)} validation cycle(s)."
            else:
                plan.novelty_context += f"\n\nPlan completed after {len(validation_history)} refinement cycles (maximum reached)."

        # Add timestamp and final formatting
        from datetime import datetime

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        plan.novelty_context += f"\nPlan finalized on {timestamp}"

        return plan

    def post(self, shared, prep_res, exec_res):
        """Mark planning as completed."""
        store = get_shared_store(shared)
        store.research_plan = exec_res
        store.planning_completed = True
        update_shared_store(shared, store)

        print("\n🎉 Research plan finalized!")
        return "default"


class PlanOutputNode(Node):
    """Generate beautiful markdown output and save to file."""

    def prep(self, shared):
        """Read finalized plan and supporting data."""
        store = get_shared_store(shared)
        return store.research_plan, store.novelty_assessment, store.final_ideas

    def exec(self, prep_res):
        """Generate beautiful markdown output."""
        plan, novelty_assessment, research_idea = prep_res

        # Generate comprehensive markdown content
        markdown_content = self._generate_beautiful_markdown(
            plan, novelty_assessment, research_idea
        )

        return markdown_content

    def _generate_beautiful_markdown(self, plan, novelty_assessment, research_idea):
        """Generate beautiful markdown with icons and formatting."""

        from datetime import datetime

        timestamp = datetime.now().strftime("%B %d, %Y")

        markdown = f"""# 📋 {plan.title}
*Generated on {timestamp}*

---

## 🎯 Executive Summary

{plan.executive_summary}

---

## 📊 Project Overview

| Attribute | Value |
|-----------|-------|
| 📝 **Project Type** | {plan.project_type.replace("_", " ").title()} |
| ⏰ **Timeline** | {plan.timeline.replace("_", " ").title()} |
| 👥 **Target Audience** | {plan.target_audience.title()} |
| 📈 **Number of Phases** | {len(plan.phases)} |

---

## 🔬 Research Context

### 💡 Original Research Idea
{research_idea}

"""

        # Add novelty assessment if available
        if novelty_assessment:
            markdown += f"""### 📊 Novelty Assessment
- **Novelty Score**: {novelty_assessment.final_novelty_score:.2f}/1.0
- **Confidence**: {novelty_assessment.confidence:.2f}
- **Papers Analyzed**: {novelty_assessment.final_papers_count}

{novelty_assessment.assessment_summary[:500]}...

"""

        # Add detailed phases
        markdown += """---

## 📅 Research Plan Phases

"""

        for phase in plan.phases:
            markdown += f"""### Phase {phase.phase_number}: {phase.title}
**Duration**: {phase.duration}

{phase.description}

#### ✅ Tasks
"""
            for task in phase.tasks:
                markdown += f"- {task}\n"

            markdown += """
#### 🎯 Deliverables
"""
            for deliverable in phase.deliverables:
                markdown += f"- {deliverable}\n"

            markdown += """
#### 🏁 Milestones
"""
            for milestone in phase.milestones:
                markdown += f"- {milestone}\n"

            markdown += "\n---\n\n"

        # Add resources and challenges
        if plan.resources_needed:
            markdown += """## 🔧 Required Resources

"""
            for resource in plan.resources_needed:
                markdown += f"- {resource}\n"
            markdown += "\n"

        if plan.potential_challenges:
            markdown += """## ⚠️ Potential Challenges & Mitigation

"""
            for challenge in plan.potential_challenges:
                markdown += f"- {challenge}\n"
            markdown += "\n"

        if plan.success_metrics:
            markdown += """## 📊 Success Metrics

"""
            for metric in plan.success_metrics:
                markdown += f"- {metric}\n"
            markdown += "\n"

        # Add related papers
        if plan.related_papers:
            markdown += """## 📚 Key References

"""
            for paper in plan.related_papers:
                markdown += f"- {paper}\n"
            markdown += "\n"

        # Add footer
        markdown += f"""---

## 📝 Plan Generation Details

- **Generated by**: AI Research Assistant
- **Planning Configuration**: {plan.project_type} project, {plan.timeline} timeline
- **Target Audience**: {plan.target_audience}

{plan.novelty_context}

---

*This research plan was generated using AI assistance. Please review and adapt as needed for your specific context and requirements.*
"""

        return markdown

    def post(self, shared, prep_res, exec_res):
        """Save markdown to file and display to user."""
        store = get_shared_store(shared)

        # Create output directory if it doesn't exist
        import os

        os.makedirs(store.plan_config.output_directory, exist_ok=True)

        # Generate filename
        if store.research_plan:
            safe_title = "".join(
                c for c in store.research_plan.title if c.isalnum() or c in (" ", "_")
            ).strip()
            safe_title = safe_title.replace(" ", "_")[:50]  # Limit length
            filename = f"{safe_title}_research_plan.md"
            filepath = os.path.join(store.plan_config.output_directory, filename)

            # Write to file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(exec_res)

            # Display completion
            print("\n🎉 RESEARCH PLAN COMPLETED!")
            print("=" * 60)
            print(f"📋 Plan Title: {store.research_plan.title}")
            print(f"📁 Saved to: {filepath}")
            print(f"📊 {len(store.research_plan.phases)} phases planned")
            print(
                f"⏰ Timeline: {store.research_plan.timeline.replace('_', ' ').title()}"
            )
            print("=" * 60)

            # Display the markdown content to stdout as well
            print("\n📄 RESEARCH PLAN CONTENT:")
            print("-" * 60)
            print(exec_res)
        else:
            print("ERROR: No research plan found in shared store")

        return "default"
