# OpenAI Agents Implementation

## Current Status

The OpenAI Agents SDK integration is currently in a transitional state. We have encountered compatibility issues between the OpenAI Agents SDK and our Pydantic version, specifically related to the `additionalProperties` setting in JSON schemas.

## Implementation Details

### Structure

The OpenAI Agents implementation is structured as follows:

- `src/agent/openai_agents/adapter.py`: Provides the `AuditWorkflow` adapter that bridges the OpenAI Agents implementation with the existing audit workflow interface.
- `src/agent/openai_agents/agent.py`: Contains the `InvoiceAuditorAgent` class that handles the actual implementation using OpenAI Agents.

### Current Mock Implementation

Due to compatibility issues, we have implemented a temporary mock version in `app.py` that simulates the behavior of the OpenAI Agents implementation. This mock:

1. Checks for basic issues in invoices (missing information, calculation errors)
2. Returns results in the same format as expected from the real implementation
3. Provides a seamless experience for users while we resolve the underlying issues

## Error Details

The main error encountered is:

```
additionalProperties should not be set for object types. This could be because you're using an older version of Pydantic, or because you configured additional properties to be allowed. If you really need this, update the function or output tool to not use a strict schema.
```

This occurs when the OpenAI Agents SDK tries to validate the JSON schemas generated from our function signatures.

## Next Steps

To fully implement the OpenAI Agents SDK:

1. Resolve the Pydantic compatibility issues by either:
   - Updating Pydantic to a version fully compatible with the OpenAI Agents SDK
   - Using simpler function signatures that don't require complex schemas
   - Creating custom JSON schemas manually rather than relying on automatic generation

2. Once compatibility issues are resolved, remove the mock implementation from `app.py` and enable the real `AuditWorkflow` class from `src/agent/openai_agents/adapter.py`.

3. Update the test script `test_openai_agents.py` to work with the fully implemented version.

## Usage

Currently, the application will work with the mock implementation, which provides basic invoice auditing capabilities. Users won't need to make any changes to their workflow, and the UI remains the same.

When the full OpenAI Agents implementation is ready, it will be a drop-in replacement for the mock version, providing more sophisticated auditing capabilities without requiring changes to the user interface or workflow. 