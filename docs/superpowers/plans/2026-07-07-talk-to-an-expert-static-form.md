# Talk to an Expert Static Form Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the HubSpot-embedded form on `talk-to-an-expert.html` with static HTML that visually and structurally matches the live rendered HubSpot form, with a front-end-only submit placeholder (no backend wired up yet).

**Architecture:** This is a single static HTML file with no build step and no test framework (per `CLAUDE.md`: pre-rendered HTML served by Apache, no active PHP/WordPress). All work happens directly inside `talk-to-an-expert.html`: replace the two `<script>` tags inside the `.contact-form` widget (lines ~1592-1603) with real form markup, add scoped CSS in a new `<style>` block, and add a small inline `<script>` for client-side validation + the placeholder success-message swap. "Testing" in this plan means starting the local dev server and driving the page with Playwright (already available as a skill/tool) to verify layout, validation, and submit behavior — there is no unit test suite to run.

**Tech Stack:** Plain HTML/CSS/vanilla JS. No frameworks, no npm, no build step. Site already loads jQuery and Elementor JS globally on this page but the new code must not depend on either — it must work as plain vanilla JS appended at the end of the existing widget.

## Global Constraints

- Only `talk-to-an-expert.html` may be modified. Do not touch `_header.html`, `_footer.html`, `contact-us/index.html`, or any other page.
- Do not run `build_header_footer.py` — this task doesn't touch header/footer templates.
- Reuse existing site design tokens instead of hardcoding new colors/fonts:
  - Pink brand color: `#D76AB3` (`--e-global-color-primary` / `--e-global-color-secondary` in `elementor-kit-7`, defined in `wp-content/uploads/elementor/css/post-7.css@ver=1780493340.css`)
  - White: `--e-global-color-1d8fa95` = `#FFFFFF`
  - Body text color: `--e-global-color-text` = `#2B2B2B`
  - Card background (already applied by existing wrapper CSS, do not redefine): `#F6F7F8`
  - Font families already loaded: `"adelle-sans"` (body/labels), `"adelle"` (headings) — do not introduce new font-family declarations
  - Sitewide button rule already exists (`elementor-kit-7 button, input[type=submit], .elementor-button`): pink pill, `border-radius:40px`, white text, hover swaps to `--e-global-color-primary`. A plain `<button type="submit">` inside the page picks this up automatically — do not override `background-color`/`border-radius` for the submit button unless matching the screenshot requires a deviation, and if so document why inline.
  - Standard responsive breakpoints used elsewhere on this page/site: `768px`, `1023px`/`1024px`, `1366px`, `2400px`. Use `767px` as the mobile single-column collapse point, consistent with sitewide `@media(max-width:767px)` usage.
- Exact dropdown option lists (verbatim, in this order):
  - **Job Function**: Please Select, Customer Success / Service Delivery, Finance, Human Resources / Internal Communications, Legal and Compliance, Marketing, Operations, Procurement / Purchasing, Product Management, Project and Programme Management, Quality Assurance, Research and Development, Sales: Pre-Sales / Business Development / Account Management, Strategy and Leadership, Technical / IT
  - **Seniority**: Please Select, C Level, Senior, Mid Level, Junior
  - **Number of Employees**: Please Select, Under 10, Below 150, Between 150 and 1500, Between 1500-5000, Above 5000
- Product/Service checkbox items (verbatim, 13 items): Fresh Intranet; Automation, Data & AI Consulting (e.g. Power Platform, Microsoft Fabric, Microsoft Copilot, Agents); Cyber Consulting (e.g. Penetration Testing, GRC, ISO, and Technology Implementation); Managed Cyber Services (e.g. SOC, NOC, MDR); Managed IT Services and Support; Software & Licensing (e.g. Microsoft CSP, E5 and E7 licenses, cyber security software); Technology Sourcing and Management (e.g. Devices, Network, Infrastructure); D365 and Business Applications Consulting; Digital Employee Experience (e.g. M365 and SharePoint migrations); Hybrid Cloud Consulting; Sovereign Cloud / Infrastructure as a Service; Unified Communications; Other (please expand in "how can we help")
- Footer-confirmed URLs to reuse: `/privacy-policy/index.html`, `/terms-of-use/index.html`
- No reCAPTCHA badge or script in the rebuilt form.
- Submit handler is a placeholder: `preventDefault()`, validate, hide form, show a "Thank you" message. No network request. Must include an HTML comment flagging this as a placeholder pending a real submission endpoint.

---

### Task 1: Replace HubSpot embed with static form markup

**Files:**
- Modify: `talk-to-an-expert.html:1592-1603` (the `.contact-form` widget currently containing the two HubSpot `<script>` tags)

**Interfaces:**
- Produces: a `<form id="expert-form" class="expert-form" novalidate>` element with fields named below, a `<div id="expert-form-success" class="expert-form-success" hidden>` confirmation block as a sibling of the form (same parent), all inside the existing `.contact-form` wrapper div. Task 3's JS queries these by `id`/`class`, so the exact names below must match.

- [ ] **Step 1: Read the exact current block to replace**

Confirm the current content at that location (already read in this session):
```html
<div class="elementor-element elementor-element-2999886 contact-form elementor-widget-mobile__width-inherit elementor-widget elementor-widget-html" data-id="2999886" data-element_type="widget" data-e-type="widget" data-widget_type="html.default">
    <div style "center">
        <script charset="utf-8" type="text/javascript" src="https://js-eu1.hsforms.net/forms/embed/v2.js"></script>
        <script>
            hbspt.forms.create({
                portalId: "3017156",
                formId: "4ab67848-62f3-41cd-a09d-7a201c55f1d5",
                region: "eu1"
            });
        </script>
    </div>
</div>
```

- [ ] **Step 2: Replace the inner `<div style "center">...</div>` with static form markup**

Use `Edit` on `talk-to-an-expert.html` with this `old_string`:
```html
                                <div style "center">
                                    <script charset="utf-8" type="text/javascript" src="https://js-eu1.hsforms.net/forms/embed/v2.js"></script>
                                    <script>
                                        hbspt.forms.create({
                                            portalId: "3017156",
                                            formId: "4ab67848-62f3-41cd-a09d-7a201c55f1d5",
                                            region: "eu1"
                                        });
                                    </script>
                                </div>
```

and this `new_string`:
```html
                                <div style="text-align:center">
                                    <!-- Static rebuild of the former HubSpot embed (portalId 3017156, formId 4ab67848-62f3-41cd-a09d-7a201c55f1d5).
                                         Submit handling below is a front-end-only placeholder: it validates the form and shows a
                                         confirmation message, but does not transmit data anywhere. Wire a real submission endpoint
                                         (e.g. HubSpot Forms Submission API) before relying on this in production. -->
                                    <form id="expert-form" class="expert-form" novalidate>
                                        <div class="expert-form-row">
                                            <div class="expert-form-field">
                                                <label for="ef-first-name">First Name*</label>
                                                <input type="text" id="ef-first-name" name="firstname" required>
                                            </div>
                                            <div class="expert-form-field">
                                                <label for="ef-last-name">Last Name*</label>
                                                <input type="text" id="ef-last-name" name="lastname" required>
                                            </div>
                                        </div>
                                        <div class="expert-form-row">
                                            <div class="expert-form-field">
                                                <label for="ef-job-function">Job Function*</label>
                                                <select id="ef-job-function" name="job_function" required>
                                                    <option value="" selected disabled>Please Select</option>
                                                    <option value="Customer Success / Service Delivery">Customer Success / Service Delivery</option>
                                                    <option value="Finance">Finance</option>
                                                    <option value="Human Resources / Internal Communications">Human Resources / Internal Communications</option>
                                                    <option value="Legal and Compliance">Legal and Compliance</option>
                                                    <option value="Marketing">Marketing</option>
                                                    <option value="Operations">Operations</option>
                                                    <option value="Procurement / Purchasing">Procurement / Purchasing</option>
                                                    <option value="Product Management">Product Management</option>
                                                    <option value="Project and Programme Management">Project and Programme Management</option>
                                                    <option value="Quality Assurance">Quality Assurance</option>
                                                    <option value="Research and Development">Research and Development</option>
                                                    <option value="Sales: Pre-Sales / Business Development / Account Management">Sales: Pre-Sales / Business Development / Account Management</option>
                                                    <option value="Strategy and Leadership">Strategy and Leadership</option>
                                                    <option value="Technical / IT">Technical / IT</option>
                                                </select>
                                            </div>
                                            <div class="expert-form-field">
                                                <label for="ef-seniority">Seniority*</label>
                                                <select id="ef-seniority" name="seniority" required>
                                                    <option value="" selected disabled>Please Select</option>
                                                    <option value="C Level">C Level</option>
                                                    <option value="Senior">Senior</option>
                                                    <option value="Mid Level">Mid Level</option>
                                                    <option value="Junior">Junior</option>
                                                </select>
                                            </div>
                                        </div>
                                        <div class="expert-form-row">
                                            <div class="expert-form-field">
                                                <label for="ef-email">Business Email*</label>
                                                <input type="email" id="ef-email" name="email" required>
                                            </div>
                                            <div class="expert-form-field">
                                                <label for="ef-company">Company Name*</label>
                                                <input type="text" id="ef-company" name="company" required>
                                            </div>
                                        </div>
                                        <div class="expert-form-field expert-form-field--full">
                                            <span class="expert-form-group-label">Product/Service*</span>
                                            <div class="expert-form-checkboxes" id="ef-product-service">
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Fresh Intranet"> Fresh Intranet</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Automation, Data &amp; AI Consulting"> Automation, Data &amp; AI Consulting (e.g. Power Platform, Microsoft Fabric, Microsoft Copilot, Agents)</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Cyber Consulting"> Cyber Consulting (e.g. Penetration Testing, GRC, ISO, and Technology Implementation)</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Managed Cyber Services"> Managed Cyber Services (e.g. SOC, NOC, MDR)</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Managed IT Services and Support"> Managed IT Services and Support</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Software &amp; Licensing"> Software &amp; Licensing (e.g. Microsoft CSP, E5 and E7 licenses, cyber security software)</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Technology Sourcing and Management"> Technology Sourcing and Management (e.g. Devices, Network, Infrastructure)</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="D365 and Business Applications Consulting"> D365 and Business Applications Consulting</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Digital Employee Experience"> Digital Employee Experience (e.g. M365 and SharePoint migrations)</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Hybrid Cloud Consulting"> Hybrid Cloud Consulting</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Sovereign Cloud / Infrastructure as a Service"> Sovereign Cloud / Infrastructure as a Service</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Unified Communications"> Unified Communications</label>
                                                <label class="expert-form-checkbox"><input type="checkbox" name="product_service" value="Other"> Other (please expand in "how can we help")</label>
                                            </div>
                                            <span class="expert-form-error" id="ef-product-service-error" hidden>Please select at least one option.</span>
                                        </div>
                                        <div class="expert-form-field expert-form-field--full">
                                            <label for="ef-employees">Number of Employees*</label>
                                            <select id="ef-employees" name="number_of_employees" required>
                                                <option value="" selected disabled>Please Select</option>
                                                <option value="Under 10">Under 10</option>
                                                <option value="Below 150">Below 150</option>
                                                <option value="Between 150 and 1500">Between 150 and 1500</option>
                                                <option value="Between 1500-5000">Between 1500-5000</option>
                                                <option value="Above 5000">Above 5000</option>
                                            </select>
                                        </div>
                                        <div class="expert-form-row">
                                            <div class="expert-form-field">
                                                <label for="ef-help">How can we help?*</label>
                                                <textarea id="ef-help" name="how_can_we_help" required></textarea>
                                            </div>
                                            <div class="expert-form-field">
                                                <label for="ef-hear">How did you hear about us?*</label>
                                                <textarea id="ef-hear" name="how_did_you_hear" required></textarea>
                                            </div>
                                        </div>
                                        <p class="expert-form-consent-text">You can withdraw your consent at any time by clicking the Manage Preferences link in emails or emailing <a href="mailto:hello@advania.co.uk">hello@advania.co.uk</a>.</p>
                                        <label class="expert-form-checkbox expert-form-checkbox--consent">
                                            <input type="checkbox" name="marketing_consent">
                                            I agree to receive marketing updates about Advania from the Advania UK group.
                                        </label>
                                        <p class="expert-form-legal-text">For more information, please see our <a href="/terms-of-use/index.html" data-wpel-link="internal">Terms of Use</a> and <a href="/privacy-policy/index.html" data-wpel-link="internal">Privacy Policy</a>.<br>
                                        By clicking submit below, you consent to allow Advania to store and process the personal information submitted above to provide you the content requested.</p>
                                        <button type="submit" class="expert-form-submit">Connect now</button>
                                    </form>
                                    <div id="expert-form-success" class="expert-form-success" hidden>
                                        <p>Thanks for reaching out — a member of the team will be in touch shortly.</p>
                                    </div>
                                </div>
```

- [ ] **Step 3: Verify the file still has balanced tags around the edit**

Run:
```bash
grep -n "elementor-element-2999886" talk-to-an-expert.html
```
Expected: still shows the same wrapping `<div class="elementor-element elementor-element-2999886 ...">` opening tag near line 1592, unchanged (only its inner content changed).

- [ ] **Step 4: Commit**

```bash
git add talk-to-an-expert.html
git commit -m "feat(talk-to-an-expert): replace HubSpot embed with static form markup"
```

---

### Task 2: Add scoped CSS for the static form

**Files:**
- Modify: `talk-to-an-expert.html` — add a new `<style>` block immediately before the closing `</head>` tag (find the exact line with a targeted search in Step 1; do not guess the line number since Task 1 shifted line numbers).

**Interfaces:**
- Consumes: element/class names produced in Task 1 (`.expert-form`, `.expert-form-row`, `.expert-form-field`, `.expert-form-field--full`, `.expert-form-group-label`, `.expert-form-checkboxes`, `.expert-form-checkbox`, `.expert-form-checkbox--consent`, `.expert-form-error`, `.expert-form-consent-text`, `.expert-form-legal-text`, `.expert-form-submit`, `.expert-form-success`).
- Produces: visual layout only. No new class names are introduced beyond what Task 1 already defines.

- [ ] **Step 1: Locate the exact insertion point**

Run:
```bash
grep -n "</head>" talk-to-an-expert.html
```
Take the line number reported (call it `N`). The new `<style>` block goes immediately before that line.

- [ ] **Step 2: Insert the CSS block**

Use `Edit` with `old_string` set to the literal `</head>` line and `new_string` prepending this block before it:

```html
    <style id="expert-form-static-css">
        .expert-form { max-width: 700px; margin: 0 auto; text-align: left; }
        .expert-form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0 1.5em;
        }
        .expert-form-field { margin-bottom: 1.25em; display: flex; flex-direction: column; }
        .expert-form-field--full { grid-column: 1 / -1; }
        .expert-form-field label,
        .expert-form-group-label {
            font-weight: 700;
            margin-bottom: 0.4em;
            color: var(--e-global-color-text, #2B2B2B);
        }
        .expert-form-field input[type="text"],
        .expert-form-field input[type="email"],
        .expert-form-field select,
        .expert-form-field textarea {
            border: 1px solid #cccccc;
            border-radius: 4px;
            padding: 0.65em 0.75em;
            font-family: inherit;
            font-size: 16px;
            width: 100%;
            box-sizing: border-box;
            background-color: #ffffff;
        }
        .expert-form-field textarea { min-height: 3em; resize: vertical; }
        .expert-form-checkboxes { display: flex; flex-direction: column; gap: 0.75em; margin-top: 0.5em; }
        .expert-form-checkbox {
            display: flex;
            align-items: flex-start;
            gap: 0.6em;
            font-weight: 400;
            cursor: pointer;
        }
        .expert-form-checkbox input[type="checkbox"] { margin-top: 0.2em; flex-shrink: 0; }
        .expert-form-checkbox--consent { margin: 1em 0; }
        .expert-form-error {
            display: block;
            color: #c0392b;
            font-size: 14px;
            margin-top: 0.5em;
        }
        .expert-form-consent-text,
        .expert-form-legal-text {
            font-size: 14px;
            line-height: 1.5;
            margin: 1em 0;
        }
        .expert-form-submit {
            margin-top: 0.5em;
            border: none;
            cursor: pointer;
        }
        .expert-form-success {
            max-width: 700px;
            margin: 0 auto;
            text-align: center;
            padding: 2em 0;
        }
        @media (max-width: 767px) {
            .expert-form-row { grid-template-columns: 1fr; }
        }
    </style>
</head>
```

- [ ] **Step 3: Verify the style block was inserted correctly**

Run:
```bash
grep -n "expert-form-static-css" talk-to-an-expert.html
```
Expected: one match, immediately followed (within a few lines) by a single `</head>` match from `grep -n "</head>" talk-to-an-expert.html` (still exactly one `</head>` in the file).

- [ ] **Step 4: Commit**

```bash
git add talk-to-an-expert.html
git commit -m "style(talk-to-an-expert): add scoped CSS for static form layout"
```

---

### Task 3: Add client-side validation and placeholder submit behavior

**Files:**
- Modify: `talk-to-an-expert.html` — add a new `<script>` block immediately before the closing `</body>` tag (locate exact line via search, do not guess).

**Interfaces:**
- Consumes: `#expert-form`, `#ef-product-service` (checkbox group container), `#ef-product-service-error`, `#expert-form-success` from Task 1.
- Produces: no new markup; purely behavioral. No global variables/functions exposed beyond the IIFE scope.

- [ ] **Step 1: Locate the exact insertion point**

Run:
```bash
grep -n "</body>" talk-to-an-expert.html
```
Take the reported line number. The new `<script>` goes immediately before that line (this file has a single `</body>` at the very end).

- [ ] **Step 2: Insert the validation/submit script**

Use `Edit` with `old_string` set to the literal `</body>` line and `new_string` prepending this block before it:

```html
    <script id="expert-form-static-js">
        (function () {
            var form = document.getElementById('expert-form');
            if (!form) return;

            var productServiceGroup = document.getElementById('ef-product-service');
            var productServiceError = document.getElementById('ef-product-service-error');
            var successMessage = document.getElementById('expert-form-success');

            function hasProductServiceSelected() {
                return productServiceGroup.querySelectorAll('input[type="checkbox"]:checked').length > 0;
            }

            form.addEventListener('submit', function (event) {
                event.preventDefault();

                var nativeValid = form.checkValidity();
                var groupValid = hasProductServiceSelected();

                productServiceError.hidden = groupValid;

                if (!nativeValid) {
                    form.reportValidity();
                    return;
                }
                if (!groupValid) {
                    return;
                }

                form.hidden = true;
                successMessage.hidden = false;
            });

            productServiceGroup.addEventListener('change', function () {
                if (hasProductServiceSelected()) {
                    productServiceError.hidden = true;
                }
            });
        })();
    </script>
</body>
```

- [ ] **Step 3: Verify the script block was inserted correctly**

Run:
```bash
grep -n "expert-form-static-js" talk-to-an-expert.html
```
Expected: one match, and `grep -n "</body>" talk-to-an-expert.html` still shows exactly one `</body>` in the file, after the new script.

- [ ] **Step 4: Commit**

```bash
git add talk-to-an-expert.html
git commit -m "feat(talk-to-an-expert): add client-side validation and placeholder submit"
```

---

### Task 4: Manual/Playwright verification against the reference screenshots

**Files:**
- No file changes. This task only verifies Tasks 1-3.

**Interfaces:**
- Consumes: the running local dev server at `http://127.0.0.1:5500/talk-to-an-expert.html` (per `CLAUDE.md`, `python server.py` serves this).

- [ ] **Step 1: Start the local dev server**

Run (background):
```bash
python server.py
```
Expected: server listening on `http://127.0.0.1:5500/`.

- [ ] **Step 2: Load the page and take a full-page screenshot at desktop width**

Use the Playwright skill/tool to navigate to `http://127.0.0.1:5500/talk-to-an-expert.html`, resize to 1920x1080, and screenshot the form section. Compare visually against the two reference screenshots provided earlier in the conversation:
- Two-column First/Last Name, Job Function/Seniority, Business Email/Company Name rows
- Full-width Product/Service checkbox list with all 13 items
- Number of Employees full-width dropdown
- Two-column "How can we help?" / "How did you hear about us?" textareas
- Consent checkbox + legal text
- Pink pill "Connect now" button, white text, rounded

- [ ] **Step 3: Verify dropdown option lists render exactly as specified**

Use Playwright to open each `<select>` (`#ef-job-function`, `#ef-seniority`, `#ef-employees`) and read back the `<option>` text list. Confirm it matches the Global Constraints section verbatim, in order.

- [ ] **Step 4: Verify native required-field validation blocks empty submit**

Use Playwright to click the "Connect now" button with all fields empty. Expected: the browser's native validation bubble appears on the first invalid field (e.g. First Name), and `#expert-form-success` remains `hidden` (form is not replaced).

- [ ] **Step 5: Verify the Product/Service "at least one" custom validation**

Fill in every required text/select field except leave all Product/Service checkboxes unchecked, then submit. Expected: `#ef-product-service-error` becomes visible with text "Please select at least one option.", and the form remains visible (not replaced by the success message).

- [ ] **Step 6: Verify full valid submission shows the success state**

Fill in every required field, check at least one Product/Service checkbox, and submit. Expected: `#expert-form` becomes `hidden`, `#expert-form-success` becomes visible showing the thank-you text, and no network request is fired (check via Playwright's network monitoring that no POST/XHR occurs on submit).

- [ ] **Step 7: Verify responsive collapse at mobile width**

Resize the Playwright browser to 375px width and reload. Expected: all two-column rows (`expert-form-row`) collapse to a single column, matching the rest of the site's `max-width:767px` breakpoint behavior, with no horizontal overflow.

- [ ] **Step 8: Report results**

Summarize pass/fail for each of Steps 2-7 back to the user in the conversation. Do not commit anything in this task — it is verification-only. If any step fails, fix the relevant Task 1-3 file section and re-run the failing step before proceeding.

---

## Self-Review Notes

- **Spec coverage:** All spec sections covered — field order/structure (Task 1), reCAPTCHA dropped (Task 1, no badge markup added), validation + placeholder submit (Task 3), styling reusing site tokens (Task 2), scope limited to `talk-to-an-expert.html` (all tasks), placeholder HTML comment included (Task 1 Step 2).
- **Placeholder scan:** No TBD/TODO markers; all code blocks are complete and copy-pasteable.
- **Type/name consistency:** `#expert-form`, `#ef-product-service`, `#ef-product-service-error`, `#expert-form-success` are defined in Task 1 and consumed identically (same IDs) in Task 3. Class names introduced in Task 1 (`.expert-form*`) match exactly what Task 2's CSS selectors target.
