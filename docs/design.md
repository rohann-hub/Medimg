# Project: AI-Assisted Medical Imaging and Diagnosis System
## Task: Design and Implement a Premium Landing Page and Matching Login Page

I have provided a reference image of a healthcare technology website. Use this image as the primary visual inspiration for designing my project's landing page and login page.

First, carefully inspect my existing project structure, frontend framework, routing, components, authentication implementation, and current dashboard before making changes.

Do not create a separate demo project. Implement everything directly in my existing project.

### 1. Design Direction

Create a premium, modern healthcare technology website inspired by the provided reference.

Follow these visual characteristics:

- Soft pastel lavender, pink, and subtle blue gradient backgrounds.
- Clean white and translucent glass-like surfaces.
- Large, bold, modern typography.
- Rounded containers and cards.
- Soft shadows and subtle borders.
- Professional spacing and alignment.
- Smooth animations and transitions.
- Minimal, elegant navigation.
- Premium healthcare technology aesthetic.

Suggested colors:
- Soft Lavender: #DCDDF5
- Pastel Pink: #F5DDEB
- Ice White: #F8F9FC
- Primary Blue: #3857F5
- Dark Text: #20243A
- Secondary Text: #777D91

Avoid excessive gradients, strong neon effects, unnecessary glowing effects, and cluttered layouts.

### 2. Landing Page

Create a complete, responsive landing page.

**Navbar**
- Project logo and name: MedImg AI.
- Navigation: Home, Features, How It Works, Technology, About.
- Login button.
- Get Started button that redirects to the login page.

**Hero Section**

Main heading:
"AI-Assisted Medical Imaging & Diagnosis"

Supporting description:
"Transform medical imaging workflows with AI-powered image analysis, intelligent classification, explainable heatmaps, and doctor-reviewed clinical decision support."

Include:
- Two prominent CTA buttons: "Get Started" and "Explore Features".
- A visually attractive medical AI illustration on the right side.
- Show a medical imaging visualization with an X-ray scan, AI analysis elements, and an explainability heatmap.
- Use subtle floating elements and smooth animations.

The hero section should follow the composition of the provided reference image.

**Features Section**

Create premium feature cards for:

1. AI-Powered Image Classification
2. Explainable AI and Grad-CAM Heatmaps
3. Medical Image Visualization
4. DICOM Image Upload and Processing
5. CT Image Segmentation
6. Doctor Review and Approval
7. Study Management
8. Audit Trail and Traceability

Use simple, professional icons and consistent card designs.

**How It Works**

Create a clean workflow visualization:

1. Upload DICOM medical images.
2. Process and validate the images.
3. Run AI-based analysis.
4. Generate predictions and explainability heatmaps.
5. Doctor reviews the AI-generated results.
6. Approve or reject the recommendation.

**Technology Section**

Showcase the technologies used in the project, based on the actual repository and implementation.

**About Section**

Explain the purpose of MedImg AI and its educational/research focus.

**Footer**

Include:
- Project logo.
- Short project description.
- Navigation links.
- Technology information.
- Educational-use disclaimer.

### 3. Login Page

Create a separate, fully responsive login page using exactly the same design system as the landing page.

Design requirements:

- Pastel lavender and pink gradient background.
- Centered or split-screen login card.
- Glass-like white card with subtle shadows.
- MedImg AI logo and branding.
- Heading: "Welcome Back"
- Subtitle: "Sign in to access your medical imaging workspace."
- Username field.
- Password field with show/hide functionality.
- Remember me option if supported.
- Sign In button.
- Loading state and error messages.
- Responsive layout for desktop, tablet, and mobile.

Include a subtle medical AI illustration or visual element alongside the login form.

### 4. Authentication Integration

IMPORTANT: Inspect my existing backend authentication implementation before integrating the login page.

My application already has FastAPI-based authentication and JWT token functionality.

Requirements:
- Use the existing login API endpoint.
- Do not create another authentication system.
- Do not hardcode usernames or passwords.
- Handle invalid credentials properly.
- Store and manage authentication tokens using the existing application's authentication approach.
- Redirect authenticated users to the existing dashboard/worklist.
- Prevent unauthorized access to protected routes.
- Preserve existing clinician and admin role permissions.

Do not assume API endpoints. Inspect the backend code and use the actual implemented endpoints.

### STRICT DEVELOPMENT RULES

Work ONLY inside the frontend/ directory.

DO NOT open, edit, modify, rename, delete, or create anything inside backend/.

Do not modify backend APIs, authentication logic, database, AI models, or inference pipeline.

Inspect the existing frontend structure before making changes.

Reuse existing components, dependencies, routing, and API integrations wherever possible.

Do not break the existing dashboard or its functionality.

Do not create a separate demo project.

### 5. Navigation and Functionality

- Landing page Get Started → Login page.
- Landing page Login → Login page.
- Successful login → Existing application dashboard.
- Logout → Login page.
- Protected dashboard routes must continue working.
- All navigation links and buttons must work.
- Maintain existing application functionality.

### 6. Technical Requirements

- Use the existing frontend framework and dependencies.
- Reuse existing components wherever possible.
- Follow a clean, modular, maintainable component structure.
- Avoid unnecessary dependencies.
- Ensure responsive design.
- Optimize image and animation performance.
- Use accessible forms, labels, and keyboard navigation.
- Maintain proper routing.
- Do not break existing API integrations.

### 7. Important Restrictions

- Do not modify the backend authentication logic unless absolutely necessary.
- Do not change the AI inference pipeline.
- Do not change the DICOM upload workflow.
- Do not modify the database schema.
- Do not remove existing dashboard features.
- Do not introduce fake statistics, fake hospital partnerships, or fabricated accuracy claims.
- Clearly display: "Educational / Research Use Only. Not a Medical Device."
- AI predictions must be presented as decision support requiring doctor review, not as confirmed medical diagnoses.

### 8. Final Quality Requirements

Before completing the work:

1. Inspect the existing frontend and backend architecture.
2. Implement the landing page and login page.
3. Ensure both pages share the same design system.
4. Test all navigation and authentication flows.
5. Verify that the existing dashboard still works.
6. Test responsiveness at desktop, tablet, and mobile sizes.
7. Fix console errors, broken routes, and styling issues.
8. Provide a summary of all modified and created files.

**Final design goal:**

The final result should look like a premium healthcare technology startup website, following the visual direction of my provided reference image while being specifically designed for MedImg AI.

The landing page should create a strong first impression, and the login page should feel like a natural continuation of the same website—not a completely different application.