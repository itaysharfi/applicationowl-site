"""
Comprehensive site validation for applicationowl.com
Checks: layout, mobile, links, colors, spacing, fonts, grammar,
Chicago Manual of Style, and sales copy principles.
"""

import re
import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

SITE = "http://localhost:8000"
PAGES = ["index.html", "ai-coach.html", "coached-plan.html", "pricing.html"]
PASS = "\033[92mPASS\033[0m"
FAIL = "\033[91mFAIL\033[0m"
WARN = "\033[93mWARN\033[0m"

results = {"pass": 0, "fail": 0, "warn": 0}


def check(label, passed, detail="", warn_only=False):
    if passed:
        results["pass"] += 1
        print(f"  {PASS} {label}")
    elif warn_only:
        results["warn"] += 1
        print(f"  {WARN} {label}: {detail}")
    else:
        results["fail"] += 1
        print(f"  {FAIL} {label}: {detail}")


def load_html_files():
    site_dir = Path(__file__).parent.parent
    pages = {}
    for name in PAGES:
        pages[name] = (site_dir / name).read_text()
    pages["style.css"] = (site_dir / "css" / "style.css").read_text()
    return pages


def validate_links(pages):
    """Check all internal links point to valid files, no broken hrefs."""
    print("\n== LINKS ==")
    valid_targets = set(PAGES) | {"/", "#STRIPE_AI_COACH_LINK"}

    for page_name, html in pages.items():
        if page_name == "style.css":
            continue
        hrefs = re.findall(r'href="([^"]*)"', html)
        for href in hrefs:
            if href.startswith("mailto:") or href.startswith("http"):
                continue
            if href == "/":
                continue
            if href == "#STRIPE_AI_COACH_LINK":
                continue
            if href.startswith("css/") or href.startswith("images/"):
                continue  # asset references, not page links
            # Strip leading slash
            clean = href.lstrip("/")
            check(
                f"[{page_name}] link {href}",
                clean in PAGES,
                f"points to {href} which is not a valid page"
            )

    # Check no links to old Wix pages
    for page_name, html in pages.items():
        if page_name == "style.css":
            continue
        check(
            f"[{page_name}] no Wix references",
            "wix" not in html.lower() and "pricing-plans" not in html.lower(),
            "Found Wix or old pricing-plans reference"
        )

    # Check no blog links (blog removed)
    for page_name, html in pages.items():
        if page_name == "style.css":
            continue
        check(
            f"[{page_name}] no blog link",
            "/blog" not in html,
            "Found blog link - blog was removed"
        )


def validate_stripe_placeholders(pages):
    """Verify Stripe links are in the right places."""
    print("\n== STRIPE / PAYMENT LINKS ==")

    # index.html should have 2 Stripe links (hero + pricing CTA)
    count = pages["index.html"].count("#STRIPE_AI_COACH_LINK")
    check("index.html has 2 Stripe placeholders", count == 2, f"found {count}")

    # ai-coach.html should have 2 Stripe links (hero + pricing CTA)
    count = pages["ai-coach.html"].count("#STRIPE_AI_COACH_LINK")
    check("ai-coach.html has 2 Stripe placeholders", count == 2, f"found {count}")

    # pricing.html should have 1 Stripe link (AI Coach card)
    count = pages["pricing.html"].count("#STRIPE_AI_COACH_LINK")
    check("pricing.html has 1 Stripe placeholder", count == 1, f"found {count}")

    # coached-plan.html should have 0 Stripe links (all mailto)
    count = pages["coached-plan.html"].count("#STRIPE_AI_COACH_LINK")
    check("coached-plan.html has 0 Stripe placeholders", count == 0, f"found {count}")

    # Coached plan CTAs should be mailto
    check(
        "coached-plan.html CTA is mailto",
        "mailto:info@applicationowl.com" in pages["coached-plan.html"],
        "Missing mailto CTA"
    )

    # pricing.html Coached Plan CTA should be mailto
    check(
        "pricing.html Coached Plan CTA is mailto",
        'href="mailto:info@applicationowl.com"' in pages["pricing.html"],
        "Missing mailto CTA for Coached Plan"
    )


def validate_section_colors(pages):
    """Check that sections alternate white/gray properly (no two same-bg sections in a row)."""
    print("\n== SECTION COLOR ALTERNATION ==")

    for page_name, html in pages.items():
        if page_name == "style.css":
            continue
        # Extract section tags in order
        sections = re.findall(r'<section([^>]*)>', html)
        prev_is_alt = None
        bad = False
        for i, attrs in enumerate(sections):
            is_alt = 'class="alt"' in attrs
            is_special = "hero" in attrs or "social-proof" in attrs
            if is_special:
                prev_is_alt = None  # special sections break the pattern
                continue
            if prev_is_alt is not None and is_alt == prev_is_alt:
                bad = True
                check(
                    f"[{page_name}] section {i+1} alternation",
                    False,
                    f"two {'gray' if is_alt else 'white'} sections in a row"
                )
            prev_is_alt = is_alt
        if not bad:
            check(f"[{page_name}] section colors alternate properly", True)


def validate_grammar_and_style(pages):
    """Check Chicago Manual of Style and grammar issues."""
    print("\n== GRAMMAR & CHICAGO MANUAL OF STYLE ==")

    for page_name, html in pages.items():
        if page_name == "style.css":
            continue

        # Extract visible text (strip tags)
        text = re.sub(r'<[^>]+>', ' ', html)
        text = re.sub(r'&[a-z]+;', ' ', text)
        text = re.sub(r'\s+', ' ', text).strip()

        # No em dashes or en dashes (user preference)
        check(
            f"[{page_name}] no em/en dashes",
            '\u2014' not in html and '\u2013' not in html and '&mdash;' not in html and '&ndash;' not in html,
            "Found em dash or en dash - use ' - ' instead"
        )

        # No double spaces in actual visible text (exclude scripts/styles)
        html_no_script = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL)
        html_no_script = re.sub(r'<style[^>]*>.*?</style>', '', html_no_script, flags=re.DOTALL)
        visible_lines = re.findall(r'>([^<]+)<', html_no_script)
        double_space_found = any('  ' in line.strip() for line in visible_lines if line.strip() and len(line.strip()) > 2)
        check(
            f"[{page_name}] no double spaces in text",
            not double_space_found,
            "Found double spaces in visible text"
        )

        # Chicago: headline case for section titles (major words capitalized)
        titles = re.findall(r'class="section-title">([^<]+)<', html)
        for title in titles:
            words = title.split()
            # Minor words that can be lowercase (Chicago)
            minor = {"a", "an", "the", "and", "but", "or", "nor", "for", "yet", "so",
                      "at", "by", "in", "of", "on", "to", "up", "vs", "vs."}
            bad_words = []
            for j, w in enumerate(words):
                clean_w = w.strip("?.,!:")
                if j == 0:  # First word always capitalized
                    if clean_w[0].islower():
                        bad_words.append(w)
                elif clean_w.lower() in minor:
                    continue  # OK to be lowercase
                elif clean_w[0].islower() and not clean_w[0].isdigit():
                    bad_words.append(w)
            check(
                f"[{page_name}] title case: \"{title}\"",
                len(bad_words) == 0,
                f"words should be capitalized: {bad_words}",
                warn_only=True
            )

        # Check for common grammar issues
        # "it's" vs "its" - hard to auto-check, skip
        # Sentence-ending periods in feature descriptions
        feature_descs = re.findall(r'<p>([^<]{20,})</p>', html)
        for desc in feature_descs:
            desc = desc.strip()
            if desc and not desc.endswith('.') and not desc.endswith('!') and not desc.endswith('?') and 'mailto:' not in desc and 'href' not in desc:
                check(
                    f"[{page_name}] sentence ends with punctuation",
                    False,
                    f"\"{desc[:60]}...\" missing period",
                    warn_only=True
                )


def validate_copy_principles(pages):
    """Check sales copy fundamentals: promise, objection handling, social proof, CTA clarity."""
    print("\n== SALES COPY PRINCIPLES ==")

    # === HOMEPAGE ===
    html = pages["index.html"]

    # 1. Clear promise in hero (should mention the outcome, not just the product)
    hero_match = re.search(r'<h1>([^<]+)</h1>', html)
    hero_text = hero_match.group(1) if hero_match else ""
    check(
        "Homepage hero has outcome-focused headline",
        any(w in hero_text.lower() for w in ["interview", "landing", "hired", "job", "career"]),
        f"Hero: \"{hero_text}\" - should promise a clear outcome"
    )

    # 2. Social proof present
    check(
        "Homepage has social proof section",
        "social-proof" in html,
        "Missing social proof section"
    )
    check(
        "Homepage has testimonials",
        "testimonial" in html,
        "Missing testimonials"
    )

    # 3. Objection handling - money-back guarantee
    check(
        "Homepage addresses price objection (money-back guarantee)",
        "money-back" in html.lower(),
        "Missing money-back guarantee"
    )
    check(
        "Homepage addresses commitment objection (cancel anytime)",
        "cancel anytime" in html.lower(),
        "Missing cancel-anytime language"
    )

    # 4. Credibility / authority
    check(
        "Homepage has credibility section",
        "google" in html.lower() and "itay" in html.lower(),
        "Missing founder credibility"
    )

    # 5. Clear CTA with price
    check(
        "Homepage hero CTA includes price",
        "$25" in html.split("</section>")[0],
        "Hero CTA should include price to set expectations"
    )

    # 6. FAQ addresses common objections
    faq_text = html[html.find("FAQ"):]
    check(
        "FAQ addresses 'how is this different' objection",
        "different" in faq_text.lower(),
        "Missing differentiation FAQ"
    )
    check(
        "FAQ addresses 'what do I get' question",
        "what do i get" in faq_text.lower() or "what do I get" in faq_text,
        "Missing 'what do I get' FAQ"
    )
    check(
        "FAQ addresses cancellation concern",
        "cancel" in faq_text.lower(),
        "Missing cancellation FAQ"
    )

    # 7. Upsell path to Coached Plan
    check(
        "Homepage has Coached Plan teaser",
        "coached plan" in html.lower() and "teaser" in html.lower(),
        "Missing Coached Plan upsell path"
    )

    # === AI COACH PAGE ===
    html = pages["ai-coach.html"]
    check(
        "AI Coach page has 'Who It's For' section",
        "who it" in html.lower(),
        "Missing target audience section"
    )
    check(
        "AI Coach page has comparison table",
        "comparison-table" in html,
        "Missing competitive comparison"
    )
    check(
        "AI Coach page has testimonials",
        "testimonial" in html,
        "Missing testimonials"
    )
    check(
        "AI Coach page has pricing CTA at bottom",
        "pricing-cta" in html,
        "Missing bottom CTA"
    )

    # === COACHED PLAN PAGE ===
    html = pages["coached-plan.html"]
    check(
        "Coached Plan has 'How It Works' section",
        "how it works" in html.lower(),
        "Missing process explanation"
    )
    check(
        "Coached Plan has credibility / coach bio",
        "your coach" in html.lower() or "itay sharfi" in html.lower(),
        "Missing coach credibility"
    )
    check(
        "Coached Plan CTA is discovery call (not direct purchase)",
        "discovery call" in html.lower(),
        "Coached Plan should lead with discovery call, not direct purchase"
    )

    # === PRICING PAGE ===
    html = pages["pricing.html"]
    check(
        "Pricing page shows both plans",
        "coached plan" in html.lower() and "ai coach" in html.lower(),
        "Missing one of the two plans"
    )
    check(
        "Pricing page has fair use policy",
        "fair use" in html.lower(),
        "Missing fair use policy"
    )


def validate_visual(page_obj, page_name):
    """Run visual checks via Playwright: font sizes, spacing, overflow, colors."""

    # Check no horizontal overflow
    overflow = page_obj.evaluate("""
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    """)
    check(f"[{page_name}] no horizontal overflow", not overflow, "Page has horizontal scroll")

    # Check all images load (if any)
    broken_images = page_obj.evaluate("""
        () => [...document.querySelectorAll('img')].filter(i => !i.complete || i.naturalWidth === 0).length
    """)
    check(f"[{page_name}] all images load", broken_images == 0, f"{broken_images} broken images")

    # Check no text smaller than 14px
    small_text = page_obj.evaluate("""
        () => {
            const small = [];
            document.querySelectorAll('p, li, td, span, a, blockquote').forEach(el => {
                const size = parseFloat(getComputedStyle(el).fontSize);
                if (size < 14 && el.offsetParent !== null && el.textContent.trim()) {
                    small.push({tag: el.tagName, text: el.textContent.trim().substring(0, 40), size: size});
                }
            });
            return small;
        }
    """)
    check(
        f"[{page_name}] no text smaller than 14px",
        len(small_text) == 0,
        f"found {len(small_text)} elements: {small_text[:3]}",
        warn_only=True
    )

    # Check line-height is at least 1.4 for body text
    bad_line_height = page_obj.evaluate("""
        () => {
            const bad = [];
            document.querySelectorAll('p, li, blockquote').forEach(el => {
                const lh = parseFloat(getComputedStyle(el).lineHeight);
                const fs = parseFloat(getComputedStyle(el).fontSize);
                if (lh / fs < 1.4 && el.offsetParent !== null && el.textContent.trim()) {
                    bad.push({tag: el.tagName, ratio: (lh/fs).toFixed(2), text: el.textContent.trim().substring(0, 30)});
                }
            });
            return bad;
        }
    """)
    check(
        f"[{page_name}] line-height >= 1.4 for body text",
        len(bad_line_height) == 0,
        f"found {len(bad_line_height)} elements with tight line-height: {bad_line_height[:3]}",
        warn_only=True
    )

    # Check buttons have minimum 44px touch target
    small_buttons = page_obj.evaluate("""
        () => {
            const bad = [];
            document.querySelectorAll('.btn, button, a.btn').forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.height < 44 && el.offsetParent !== null) {
                    bad.push({text: el.textContent.trim().substring(0, 30), height: Math.round(rect.height)});
                }
            });
            return bad;
        }
    """)
    check(
        f"[{page_name}] buttons meet 44px touch target",
        len(small_buttons) == 0,
        f"buttons too small: {small_buttons}",
        warn_only=True
    )

    # Check sufficient color contrast on CTAs
    cta_contrast = page_obj.evaluate("""
        () => {
            const btn = document.querySelector('.btn-primary');
            if (!btn) return {ok: true};
            const style = getComputedStyle(btn);
            return {bg: style.backgroundColor, color: style.color};
        }
    """)
    check(f"[{page_name}] CTA button has visible styling", "bg" in cta_contrast, "")

    # Check spacing between sections (should be consistent)
    section_paddings = page_obj.evaluate("""
        () => {
            return [...document.querySelectorAll('section')].map(s => {
                const style = getComputedStyle(s);
                return {
                    paddingTop: style.paddingTop,
                    paddingBottom: style.paddingBottom,
                    className: s.className
                };
            });
        }
    """)
    # Just report, don't fail
    paddings = set()
    for s in section_paddings:
        if "hero" not in s.get("className", "") and "social-proof" not in s.get("className", ""):
            paddings.add(s["paddingTop"])
    check(
        f"[{page_name}] consistent section padding",
        len(paddings) <= 2,
        f"found {len(paddings)} different padding values: {paddings}",
        warn_only=True
    )


def validate_above_fold(page_obj, page_name, viewport_height):
    """Check what's visible above the fold - hero must be compelling."""
    fold_content = page_obj.evaluate(f"""
        () => {{
            const elements = [];
            document.querySelectorAll('h1, h2, p, a.btn, .subtext, .btn-primary').forEach(el => {{
                const rect = el.getBoundingClientRect();
                if (rect.top < {viewport_height} && el.offsetParent !== null) {{
                    elements.push({{
                        tag: el.tagName,
                        text: el.textContent.trim().substring(0, 80),
                        top: Math.round(rect.top),
                        classes: el.className
                    }});
                }}
            }});
            return elements;
        }}
    """)

    texts = [e["text"] for e in fold_content]
    all_text = " ".join(texts).lower()

    # Hero headline must be above fold
    has_h1 = any(e["tag"] == "H1" for e in fold_content)
    check(f"[{page_name}] headline visible above fold", has_h1, "H1 not visible above the fold")

    # CTA button must be above fold
    has_cta = any("btn-primary" in e.get("classes", "") for e in fold_content)
    check(f"[{page_name}] CTA button visible above fold", has_cta, "Primary CTA not visible above the fold")

    # Price or value prop should be above fold
    has_price_or_value = "$" in all_text or "free" in all_text or "guarantee" in all_text
    check(
        f"[{page_name}] price or value visible above fold",
        has_price_or_value,
        "No price or value proposition above the fold",
        warn_only=True
    )


def validate_name_context(pages):
    """Check that Itay's name always appears with context (not just dropped in)."""
    print("\n== NAME CONTEXT CHECK ==")

    for page_name, html in pages.items():
        if page_name == "style.css":
            continue

        # Find all instances of "Itay" and check they have context nearby
        lines = html.split('\n')
        for i, line in enumerate(lines):
            if 'Itay' not in line:
                continue
            # Get surrounding context (this line)
            text = re.sub(r'<[^>]+>', '', line).strip()
            if not text:
                continue
            # Check if there's context: title, role, or company
            has_context = any(w in text.lower() for w in [
                "google", "former", "coach", "pm", "professor", "founder",
                "built by", "work directly", "your coach", "join",
                "personally", "hiring manager", "cal state"
            ])
            check(
                f"[{page_name}] Itay's name has context: \"{text[:70]}\"",
                has_context,
                "Name dropped without explaining who Itay is",
                warn_only=True
            )


def validate_creative_quality(pages):
    """Deep check on creative/copy quality."""
    print("\n== CREATIVE QUALITY ==")

    # Homepage hero - does it speak to the reader's pain?
    html = pages["index.html"]
    hero = html[:html.find('</section>')]
    hero_text = re.sub(r'<[^>]+>', ' ', hero)

    check(
        "Homepage hero addresses reader's pain (second person)",
        "you" in hero_text.lower() or "your" in hero_text.lower(),
        "Hero should speak directly to the reader"
    )

    # Check we're not leading with product features but with outcomes
    h1 = re.search(r'<h1>([^<]+)</h1>', html).group(1)
    feature_words = ["ai", "algorithm", "technology", "platform", "tool", "software"]
    outcome_words = ["interview", "landing", "hired", "job", "career", "stop", "start"]
    is_outcome = any(w in h1.lower() for w in outcome_words)
    is_feature = any(w in h1.lower() for w in feature_words)
    check(
        "Homepage H1 is outcome-focused (not feature-focused)",
        is_outcome and not is_feature,
        f"H1: \"{h1}\" - lead with what they get, not what we built"
    )

    # Check for specificity in social proof (not vague claims)
    check(
        "Social proof has specific companies",
        "google" in html.lower() and "cisco" in html.lower(),
        "Social proof should name specific companies"
    )
    check(
        "Social proof has specific numbers",
        "200+" in html,
        "Social proof should include specific numbers"
    )

    # Check testimonials are specific (mention concrete outcomes)
    testimonials = re.findall(r'<blockquote>([^<]+)</blockquote>', html)
    for t in testimonials:
        has_specifics = any(w in t.lower() for w in [
            "interview", "cisco", "google", "linkedin", "recruiter",
            "three", "100%", "phone interview", "selected"
        ])
        check(
            f"Testimonial is specific: \"{t[:50]}...\"",
            has_specifics,
            "Testimonial is too vague - should mention concrete outcomes"
        )

    # Check Coached Plan page doesn't feel like a hard sell
    cp = pages["coached-plan.html"].lower()
    disc_pos = cp.find("discovery")
    price_pos = cp.find("195")
    check(
        "Coached Plan leads with discovery call, not payment",
        disc_pos != -1 and price_pos != -1 and disc_pos < price_pos,
        "Should mention discovery call before showing price"
    )

    # Check AI Coach page shows clear differentiation
    ac = pages["ai-coach.html"]
    check(
        "AI Coach page explains what makes Owl different from ChatGPT",
        "generic" in ac.lower() or "chatgpt" in ac.lower() or "chatbot" in ac.lower(),
        "Should differentiate from generic AI tools"
    )

    # Check pricing page doesn't have decision paralysis (clear recommendation)
    pr = pages["pricing.html"]
    check(
        "Pricing page has a featured/recommended plan",
        "featured" in pr,
        "One plan should be visually highlighted as recommended"
    )


def validate_mobile_visual(context, page_name):
    """Run mobile-specific visual checks."""
    page = context.new_page()
    page.goto(f"{SITE}/{page_name}")
    page.wait_for_load_state("networkidle")

    # Check nav is collapsed (hamburger visible)
    hamburger_visible = page.evaluate("""
        () => {
            const btn = document.querySelector('.menu-toggle');
            return btn && getComputedStyle(btn).display !== 'none';
        }
    """)
    check(f"[{page_name}] mobile: hamburger menu visible", hamburger_visible, "Nav not collapsed on mobile")

    # Check nav links are hidden
    nav_hidden = page.evaluate("""
        () => {
            const nav = document.querySelector('.nav-links');
            return nav && getComputedStyle(nav).display === 'none';
        }
    """)
    check(f"[{page_name}] mobile: nav links hidden by default", nav_hidden, "Nav links showing on mobile")

    # Check no horizontal overflow on mobile
    overflow = page.evaluate("""
        () => document.documentElement.scrollWidth > document.documentElement.clientWidth
    """)
    check(f"[{page_name}] mobile: no horizontal overflow", not overflow, "Horizontal scroll on mobile")

    # Check table is not in table layout on mobile
    if "comparison-table" in page.content():
        table_display = page.evaluate("""
            () => {
                const table = document.querySelector('.comparison-table');
                return table ? getComputedStyle(table).display : 'none';
            }
        """)
        check(
            f"[{page_name}] mobile: comparison table is stacked",
            table_display == "block",
            f"Table display is {table_display}, should be block for mobile cards"
        )

    page.close()


def main():
    pages = load_html_files()

    print("=" * 60)
    print("APPLICATION OWL SITE VALIDATION")
    print("=" * 60)

    # Static checks
    validate_links(pages)
    validate_stripe_placeholders(pages)
    validate_section_colors(pages)
    validate_grammar_and_style(pages)
    validate_copy_principles(pages)
    validate_name_context(pages)
    validate_creative_quality(pages)

    # Visual checks with Playwright
    print("\n== VISUAL CHECKS (Desktop) ==")
    with sync_playwright() as p:
        browser = p.chromium.launch()

        # Desktop
        desktop_page = browser.new_page(viewport={"width": 1280, "height": 800})
        for name in PAGES:
            desktop_page.goto(f"{SITE}/{name}")
            desktop_page.wait_for_load_state("networkidle")
            validate_visual(desktop_page, name)
            validate_above_fold(desktop_page, name, 800)
        desktop_page.close()

        # Mobile
        print("\n== VISUAL CHECKS (Mobile - iPhone 12) ==")
        iphone = p.devices["iPhone 12"]
        mobile_ctx = browser.new_context(**iphone)
        for name in PAGES:
            validate_mobile_visual(mobile_ctx, name)
        mobile_ctx.close()

        browser.close()

    # Summary
    print("\n" + "=" * 60)
    total = results["pass"] + results["fail"] + results["warn"]
    print(f"RESULTS: {results['pass']}/{total} passed, {results['fail']} failed, {results['warn']} warnings")
    if results["fail"] > 0:
        print(f"\033[91m{results['fail']} FAILURES - fix these before deploying\033[0m")
        sys.exit(1)
    elif results["warn"] > 0:
        print(f"\033[93mAll critical checks passed, {results['warn']} warnings to review\033[0m")
    else:
        print("\033[92mAll checks passed!\033[0m")


if __name__ == "__main__":
    main()
