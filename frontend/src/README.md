# Frontend Folder Structure Policy

## Directory Organization

```
src/
├── app/           # Next.js App Router - page components only
├── features/      # Business domain features
├── components/    # Shared UI components
├── contexts/      # Global React contexts
├── lib/          # Shared utilities and API client
└── types/        # Global TypeScript definitions
```

## Rules

### `app/`
- **Purpose**: Next.js routing + page component implementations
- **Contains**: Route files (`page.tsx`, `layout.tsx`, `api/`)
- **Imports from**: `@/features/`, `@/components/`, `@/contexts/`

### `features/`
- **Purpose**: Business domain organization
- **Structure**: `features/{domain}/{components|hooks|services|types|utils}/`
- **Example**: `features/upload/components/FileUpload.tsx`
- **Rule**: Feature-specific code only, no cross-feature dependencies

### `components/`
- **Purpose**: Shared UI components used across features
- **Structure**: `components/{ui|layout}/`
- **Example**: `components/ui/Button.tsx`

### `contexts/`
- **Purpose**: Global React contexts (auth, theme, etc.)
- **Rule**: Only app-wide state that multiple features need

### `lib/`
- **Purpose**: Shared utilities, API client, external integrations
- **Rule**: Pure functions and cross-cutting concerns

### `types/`
- **Purpose**: Global TypeScript definitions
- **Rule**: Types used by multiple features or app-wide

## Key Principles

1. **Simple is best** - No unnecessary nesting or abstraction
2. **Feature-first** - Group by business domain, not technical layer
3. **Shared at top level** - Common code in root directories
4. **Clear ownership** - Each file has obvious purpose and location