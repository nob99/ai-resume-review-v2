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
- **Structure**: `features/{domain}/{components|hooks|types|utils}/`
- **Example**: `features/upload/components/FileUpload.tsx`
- **Rule**: Feature-specific code only, no cross-feature dependencies
- **Note**: No `services/` folders - API calls belong in `/lib/api.ts`

### `components/`
- **Purpose**: Shared UI components used across features
- **Structure**: `components/{ui|layout}/`
- **Example**: `components/ui/Button.tsx`

### `contexts/`
- **Purpose**: Global React contexts (auth, theme, etc.)
- **Rule**: Only app-wide state that multiple features need

### `lib/`
- **Purpose**: Shared utilities, API client, external integrations
- **Contains**: `api.ts` (all HTTP calls), `utils.ts`, configuration files
- **Rule**: Pure functions and cross-cutting concerns
- **API Pattern**: All backend API calls consolidated in `api.ts`

### `types/`
- **Purpose**: Global TypeScript definitions
- **Rule**: Types used by multiple features or app-wide

## Key Principles

1. **Simple is best** - No unnecessary nesting or abstraction
2. **Feature-first** - Group by business domain, not technical layer
3. **Shared at top level** - Common code in root directories
4. **Clear ownership** - Each file has obvious purpose and location
5. **Single source of truth** - No duplicate implementations (e.g., API calls only in `/lib/api.ts`)

## API Call Guidelines

### ✅ Correct Pattern
```typescript
// All API calls in lib/api.ts
import { authApi, candidateApi } from '@/lib/api'

// Components and contexts import from lib
import { authApi } from '@/lib/api'
```

### ❌ Avoid This
```typescript
// Don't create feature-specific API services
import authService from '@/features/auth/services/authService'

// Don't duplicate API implementations
```

## Import Guidelines

- **Pages**: Import from `@/features/`, `@/components/`, `@/contexts/`
- **Features**: Import from `@/lib/`, `@/components/`, `@/types/`
- **Components**: Import from `@/lib/`, `@/types/`
- **Contexts**: Import from `@/lib/`, `@/types/`