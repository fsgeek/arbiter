#!/bin/bash
# Install the OpenTimestamps client and wire up the post-commit hook.
# Idempotent: safe to re-run.
set -e

GIT_ROOT=$(git rev-parse --show-toplevel)
cd "$GIT_ROOT"

echo "Installing opentimestamps-client..."
uv pip install opentimestamps-client

echo "Installing git hooks (post-commit, post-merge)..."
HOOK="$GIT_ROOT/.git/hooks/post-commit"
cat > "$HOOK" << 'EOF'
#!/bin/bash
exec "$(git rev-parse --show-toplevel)/scripts/hooks/post-commit" "$@"
EOF
chmod +x "$HOOK"

# post-merge replaces git-lfs's own hook; scripts/hooks/post-merge runs the
# lfs step first, so nothing lfs did is lost.
HOOK="$GIT_ROOT/.git/hooks/post-merge"
cat > "$HOOK" << 'EOF'
#!/bin/bash
exec "$(git rev-parse --show-toplevel)/scripts/hooks/post-merge" "$@"
EOF
chmod +x "$HOOK"

echo "Done. Each commit now writes a timestamp proof to timestamps/."
echo "Run 'scripts/ots-upgrade.sh' a few hours after committing to anchor"
echo "the proofs to the Bitcoin blockchain."
