
#!/bin/bash

# Comprehensive Git Sync and Helper Script
# Usage: 
#   ./git-utils.sh                    - Sync current branch
#   ./git-utils.sh [branch-name]      - Sync specific branch
#   ./git-utils.sh --help             - Show help
#   ./git-utils.sh --functions         - Show available functions

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper function to print colored output
print_status() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Show help
show_help() {
    echo "Git Utils Helper Script"
    echo ""
    echo "Usage:"
    echo "  gu rebase                        - Interactive rebase guide"
    echo "  gu push_upstream                  - Push and set upstream"
    echo "  gu new_branch                    - Create new branch from latest master"
    echo "  gu pr_review <url> [--no-print-cd] - Clone/update repo for PR or branch URL"
    echo "  gu pr_review_v2 <url> [--no-print-cd] - PR or compare URL: clone/fetch, switch to PR head or branch, list changed files vs origin/master"
    echo "  gu status                        - Show detailed status"
    echo "  gu help                          - Show this help"
}

# Show available functions (alias for show_help)
show_functions() {
    show_help
    echo ""
    echo "To use these functions, source this script:"
    echo "  source scripts/git-utils.sh"
}



# Push and set upstream in one command
push_upstream() {
    local branch=$(git branch --show-current)
    
    echo ""
    print_info "🚀 PUSH OPERATION: $branch"
    echo ""
    
    # Step 1: Pre-flight checks
    print_info "📋 Step 1: Pre-flight checks"
    if git status --porcelain | grep -E '^[MADRC]'; then
        print_error "❌ You have uncommitted changes to tracked files."
        print_info "💡 Please commit or stash your changes before pushing."
        echo ""
        return 1
    fi
    print_status "✅ Working directory is clean"
    echo ""
    
    # Step 2: Check if branch has diverged from remote
    print_info "🔍 Step 2: Checking remote branch status..."
    local needs_force=false
    
    # Check if remote branch exists
    if git rev-parse --verify "origin/$branch" >/dev/null 2>&1; then
        print_info "✅ Remote branch exists: origin/$branch"
        
        # Check if branches have diverged
        local local_commit=$(git rev-parse HEAD)
        local remote_commit=$(git rev-parse "origin/$branch")
        
        if [ "$local_commit" != "$remote_commit" ]; then
            # Check if remote is ancestor of local (normal push)
            if git merge-base --is-ancestor "origin/$branch" HEAD 2>/dev/null; then
                print_info "✅ Local branch is ahead of remote (normal push)"
            else
                print_warning "⚠️  Branches have diverged - will use --force-with-lease"
                print_info "💡 This typically happens after a rebase"
                needs_force=true
            fi
        else
            print_info "✅ Local and remote are in sync"
        fi
    else
        print_info "ℹ️  Remote branch doesn't exist yet (first push)"
    fi
    echo ""
    
    # Step 3: Push operation
    print_info "📤 Step 3: Pushing branch and setting upstream..."
    if [ "$needs_force" = true ]; then
        print_warning "⚠️  Using --force-with-lease for safety"
        print_info "ℹ️  This will overwrite remote with your rebased commits"
        echo ""
        
        local push_cmd="git push -u origin $branch --force-with-lease"
        print_info "🔧 Executing: $push_cmd"
        echo ""
        
        if $push_cmd; then
            echo ""
            print_status "🎉 FORCE PUSH COMPLETED SUCCESSFULLY"
            print_info "✅ Branch $branch has been force-pushed to origin/$branch"
            print_info "✅ Upstream tracking has been set up"
            print_info "💡 Your rebased branch is now synchronized with the remote"
            echo ""
        else
            local exit_code=$?
            echo ""
            print_error "❌ FORCE PUSH FAILED (exit code: $exit_code)"
            echo ""
            
            print_info "🔍 COMMON CAUSES:"
            print_info "  • Someone else pushed to the remote branch since you last fetched"
            print_info "  • Authentication issues (check your git credentials)"
            print_info "  • Network connectivity problems"
            print_info "  • Remote branch protection rules"
            echo ""
            print_info "🔧 SUGGESTED SOLUTIONS:"
            print_info "  • Run 'git fetch origin' and check 'git status'"
            print_info "  • If remote changed, run 'gu rebase' again"
            print_info "  • Verify your git credentials: 'git config --list | grep user'"
            echo ""
            return $exit_code
        fi
    else
        print_info "ℹ️  Using normal push (no force needed)"
        echo ""
        
        local push_cmd="git push -u origin $branch"
        print_info "🔧 Executing: $push_cmd"
        echo ""
        
        if $push_cmd; then
            echo ""
            print_status "🎉 PUSH COMPLETED SUCCESSFULLY"
            print_info "✅ Branch $branch has been pushed to origin/$branch"
            print_info "✅ Upstream tracking has been set up"
            print_info "💡 Your branch is now synchronized with the remote"
            echo ""
        else
            local exit_code=$?
            echo ""
            print_error "❌ PUSH FAILED (exit code: $exit_code)"
            echo ""
            
            # Provide specific guidance based on common failure scenarios
            print_info "🔍 COMMON CAUSES:"
            if [ $exit_code -eq 1 ]; then
                print_info "  • Remote branch has diverged (try running this command again)"
                print_info "  • Authentication issues (check your git credentials)"
                print_info "  • Network connectivity problems"
                print_info "  • Remote branch protection rules"
            fi
            echo ""
            print_info "🔧 SUGGESTED SOLUTIONS:"
            print_info "  • Run 'git fetch origin' and try again"
            print_info "  • Run 'gu rebase' to rebase on remote changes"
            print_info "  • Check 'git status' for any issues"
            print_info "  • Verify your git credentials: 'git config --list | grep user'"
            echo ""
            return $exit_code
        fi
    fi
}


# Simple interactive rebase guide
rebase() {
    local branch=$(git branch --show-current)
    
    echo ""
    print_info "🔄 INTERACTIVE REBASE GUIDE: $branch"
    echo ""
    
    print_info "Follow these steps to rebase your branch:"
    echo ""
    
    print_info "📥 Step 1: Fetch latest changes"
    print_info "Run this command:"
    echo "   git fetch origin"
    echo ""
    
    print_info "🔄 Step 2: Choose your rebase method"
    print_info "For a simple rebase, run:"
    echo "   git rebase origin/master"
    echo ""
    print_info "For an interactive rebase (to squash/edit commits), run:"
    echo "   git rebase -i origin/master"
    echo ""
    
    print_info "🚀 Step 3: Force push your changes"
    print_info "After resolving any conflicts and completing the rebase, run:"
    echo "   git push origin $branch --force-with-lease"
    echo ""
    
    print_info "💡 Tips:"
    print_info "  • If you get conflicts, resolve them and run: git rebase --continue"
    print_info "  • To abort a rebase: git rebase --abort"
    print_info "  • --force-with-lease is safer than --force as it checks for remote changes"
    echo ""
}


# Check if branch has upstream
has_upstream() {
    git rev-parse --abbrev-ref --symbolic-full-name @{u} >/dev/null 2>&1
}


# Show detailed status
status_check() {
    local branch=$(git branch --show-current)
    
    echo ""
    print_info "📊 GIT STATUS REPORT: $branch"
    echo ""
    
    # Step 1: Branch information
    print_info "🌿 Step 1: Branch Information"
    print_info "Current branch: $branch"
    
    # Check upstream
    if has_upstream; then
        local upstream=$(git rev-parse --abbrev-ref --symbolic-full-name @{u})
        print_status "✅ Upstream: $upstream"
    else
        print_warning "⚠️  No upstream configured"
        print_info "💡 Use 'gu push_upstream' to set up upstream tracking"
    fi
    echo ""
    
    # Step 2: Working directory status
    print_info "📁 Step 2: Working Directory Status"
    if git status --porcelain | grep -q .; then
        print_warning "⚠️  Uncommitted changes detected:"
        git status --short
        echo ""
        print_info "💡 Commit or stash changes before pushing"
    else
        print_status "✅ Working directory is clean"
    fi
    echo ""
    
    # Step 3: Commit status
    print_info "📈 Step 3: Commit Status"
    local ahead=$(git log --oneline origin/master..HEAD --count 2>/dev/null | grep -E '^[0-9]+$' || echo "0")
    local behind=$(git log --oneline HEAD..origin/master --count 2>/dev/null | grep -E '^[0-9]+$' || echo "0")
    
    # Ensure we have valid numbers
    ahead=${ahead:-0}
    behind=${behind:-0}
    
    if [ "$ahead" -gt 0 ]; then
        print_info "📤 Commits ahead of origin/master: $ahead"
        print_info "💡 Use 'gu push_upstream' to push your changes"
    fi
    if [ "$behind" -gt 0 ]; then
        print_warning "📥 Commits behind origin/master: $behind"
        print_info "💡 Use 'gu rebase' to sync with remote changes"
    fi
    if [ "$ahead" -eq 0 ] && [ "$behind" -eq 0 ]; then
        print_status "✅ Branch is up to date with origin/master"
    fi
    echo ""
    
    # Step 4: Summary and recommendations
    print_info "🎯 Step 4: Summary & Recommendations"
    if [ "$ahead" -gt 0 ] && [ "$behind" -eq 0 ]; then
        print_status "✅ Ready to push - use 'gu push_upstream'"
    elif [ "$behind" -gt 0 ]; then
        print_warning "⚠️  Need to sync - use 'gu rebase' first"
    elif [ "$ahead" -eq 0 ] && [ "$behind" -eq 0 ]; then
        print_status "✅ Everything is up to date"
    else
        print_info "💡 Check the details above for next steps"
    fi
    echo ""
}


new_branch() {
    # Check for uncommitted changes (only modified tracked files, not untracked)
    if git status --porcelain | grep -E '^[MADRC]'; then
        print_error "❌ You have uncommitted changes to tracked files."
        print_info "💡 Please commit or stash your changes before creating a new branch."
        echo ""
        return 1
    fi
    
    # Ask for branch name
    print_info "Enter the name for the new branch:"
    read -r branch_name
    
    # Validate branch name
    if [ -z "$branch_name" ]; then
        print_error "Branch name cannot be empty"
        return 1
    fi
    
    # Check if branch already exists locally
    if git show-ref --verify --quiet refs/heads/$branch_name; then
        print_error "Branch '$branch_name' already exists locally"
        return 1
    fi
    
    # Check if branch already exists on remote
    if git show-ref --verify --quiet refs/remotes/origin/$branch_name; then
        print_error "Branch '$branch_name' already exists on remote"
        return 1
    fi
    
    print_info "Creating new branch '$branch_name' from latest remote master..."
    
    # Fetch latest changes
    print_info "Fetching latest changes from remote..."
    git fetch origin
    
    # Create and checkout new branch from origin/master
    git checkout -b $branch_name origin/master
    
    if [ $? -eq 0 ]; then
        print_status "Successfully created and checked out branch '$branch_name'"
        print_info "Branch is based on latest origin/master"
        
        # Set upstream for the new branch
        print_info "Setting upstream for branch '$branch_name'..."
        git push -u origin $branch_name
        
        if [ $? -eq 0 ]; then
            print_status "Successfully pushed branch and set upstream to origin/$branch_name"
        else
            print_warning "Branch created but failed to push and set upstream"
            print_info "You can manually push with: git push -u origin $branch_name"
        fi
    else
        print_error "Failed to create branch '$branch_name'"
        return 1
    fi
}

# PR Review - Clone/update the repo for a remote PR or branch URL
pr_review() {
    local pr_url="$1"
    local mode="${2:-}"
    local print_cd=false
    local quiet=false

    # Default behavior when running as a command: print a cd command suitable for eval.
    # (A script cannot cd your current terminal unless it's sourced.)
    if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
        if [ -z "$mode" ] || [ "$mode" = "--print-cd" ]; then
            print_cd=true
            quiet=true
        fi
    fi

    # In print-cd mode, route normal output to stderr so stdout is clean for eval.
    if [ "$quiet" = true ]; then
        exec 3>&1
        exec 1>&2
    fi
    
    if [ -z "$pr_url" ]; then
        print_error "❌ No PR URL specified"
        print_info "💡 Usage: gu pr_review <url> [--no-print-cd]"
        print_info "💡 Examples:"
        print_info "   • PR URL: gu pr_review https://git.soma.salesforce.com/a360/edc-python/pull/171"
        print_info "   • Tree URL: gu pr_review https://git.soma.salesforce.com/user/repo/tree/branch-name"
        print_info "   • cd from command: eval \"$(gu pr_review https://git.soma.salesforce.com/a360/edc-python/pull/171)\""
        if [ "$quiet" = true ]; then
            exec 1>&3
            exec 3>&-
        fi
        return 1
    fi
    
    echo ""
    print_info "🔍 PR REVIEW OPERATION"
    echo ""
    
    # Step 0: Change to reviews directory
    print_info "📁 Step 0: Setting up review environment"
    local reviews_dir="/Users/thomaschang/Documents/dev/git/reviews"
    
    # Create reviews directory if it doesn't exist
    if [ ! -d "$reviews_dir" ]; then
        print_info "Creating reviews directory: $reviews_dir"
        mkdir -p "$reviews_dir"
    fi
    
    # Change to reviews directory
    print_info "Changing to reviews directory: $reviews_dir"
    cd "$reviews_dir"
    print_status "✅ Now in reviews directory: $(pwd)"
    echo ""
    
    # Step 1: Extract PR number and repository info
    print_info "📋 Step 1: Parsing PR URL"
    
    # Clean the URL - remove @ symbol if present
    local clean_url=$(echo "$pr_url" | sed 's/^@//')
    print_info "🔧 Cleaned URL: $clean_url"
    
    # Check if this is a PR URL or a tree/branch URL
    local pr_number=""
    local branch_name=""
    local repo_url=""
    
    if echo "$clean_url" | grep -q "/pull/"; then
        # This is a PR URL
        print_info "🔍 Detected: Pull Request URL"
        pr_number=$(echo "$clean_url" | grep -o '/pull/[0-9]\+' | grep -o '[0-9]\+')
        repo_url=$(echo "$clean_url" | sed 's|/pull/[0-9][0-9]*.*||')
    elif echo "$clean_url" | grep -q "/tree/"; then
        # This is a tree/branch URL
        print_info "🔍 Detected: Tree/Branch URL"
        # IMPORTANT: Branch names can contain slashes (e.g., u/gzhang/embeddingInference).
        # Everything after "/tree/" is considered the branch name.
        branch_name="$(echo "$clean_url" | sed -n 's|.*/tree/||p')"
        repo_url=$(echo "$clean_url" | sed 's|/tree/.*||')
        print_info "🌿 Branch name: $branch_name"
    else
        print_error "❌ Unsupported URL format"
        print_info "💡 Supported formats:"
        print_info "   • PR URL: https://git.soma.salesforce.com/user/repo/pull/171"
        print_info "   • Tree URL: https://git.soma.salesforce.com/user/repo/tree/branch-name"
        return 1
    fi
    
    print_info "🔧 Extracted repository URL: $repo_url"
    
    # Convert HTTPS URL to SSH format for better authentication
    if [[ "$repo_url" =~ ^https://git\.soma\.salesforce\.com/ ]]; then
        repo_url=$(echo "$repo_url" | sed 's|https://git.soma.salesforce.com/|git@git.soma.salesforce.com:|')
        print_info "🔄 Converted to SSH format: $repo_url"
    fi

    # Some Git servers require ".git" for SSH clone URLs; add it if missing.
    if [[ "$repo_url" =~ ^git@git\.soma\.salesforce\.com: ]] && [[ "$repo_url" != *.git ]]; then
        repo_url="${repo_url}.git"
        print_info "🔄 Normalized SSH repo URL (added .git): $repo_url"
    fi
    
    if [ -z "$pr_number" ] && [ -z "$branch_name" ]; then
        print_error "❌ Could not extract PR number or branch name from URL"
        print_info "💡 Please provide a valid URL like:"
        print_info "   PR URL: https://git.soma.salesforce.com/user/repo/pull/171"
        print_info "   Tree URL: https://git.soma.salesforce.com/user/repo/tree/branch-name"
        return 1
    fi
    
    if [ -n "$pr_number" ]; then
        print_info "✅ PR Number: $pr_number"
    fi
    if [ -n "$branch_name" ]; then
        print_info "✅ Branch Name: $branch_name"
    fi
    print_info "✅ Repository: $repo_url"
    echo ""
    
    # Step 2: Clone the repository if not already present
    print_info "📥 Step 2: Setting up repository"
    
    # Create appropriate clone directory name
    if [ -n "$pr_number" ]; then
        local clone_dir="pr-review-$pr_number"
    else
        local clone_dir="branch-review-${branch_name//[^a-zA-Z0-9_-]/_}"
    fi
    
    if [ ! -d "$clone_dir" ]; then
        print_info "Cloning repository to $clone_dir..."
        print_info "🔧 Repository URL: $repo_url"
        
        if ! git clone "$repo_url" "$clone_dir"; then
            print_error "❌ Failed to clone repository"
            echo ""
            print_info "🔍 COMMON CLONING ISSUES:"
            print_info "  • Authentication: Make sure you're logged in to git"
            print_info "  • Network: Check your internet connection"
            print_info "  • Permissions: Verify you have access to this repository"
            print_info "  • URL format: Try without the @ symbol"
            echo ""
            print_info "💡 TROUBLESHOOTING:"
            print_info "  • Test manually: git clone $repo_url test-clone"
            print_info "  • Check authentication: git config --list | grep user"
            print_info "  • Try SSH instead: git clone git@git.soma.salesforce.com:a360/edc-python.git"
            return 1
        fi
        print_status "✅ Repository cloned successfully"
    else
        print_info "Repository already exists, updating..."
        cd "$clone_dir"
        git fetch origin
        cd ..
    fi
    echo ""

    local repo_path="${reviews_dir}/${clone_dir}"

    # Step 3: cd into the cloned directory
    # NOTE: This only persists if this script is sourced (functions run in your current shell).
    print_info "📂 Step 3: Entering repository directory"
    if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
        if ! cd "$repo_path"; then
            print_error "❌ Failed to cd into: $repo_path"
            if [ "$quiet" = true ]; then
                exec 1>&3
                exec 3>&-
            fi
            return 1
        fi
        print_status "✅ Now in: $(pwd)"
    else
        if [ "$print_cd" = true ]; then
            # Intended usage: eval "$(gu pr_review <url>)"
            exec 1>&3
            echo "cd \"$repo_path\""
            exec 3>&-
            return 0
        fi

        print_warning "⚠️  This script is running as a command, so it can't cd your current terminal."
        print_info "💡 Do this next:"
        echo "   cd \"$repo_path\""
    fi

    print_status "🎉 PR REVIEW READY"
    print_info "📁 Repo is at: $repo_path"
    echo ""
    if [ "$quiet" = true ]; then
        exec 1>&3
        exec 3>&-
    fi
    return 0
}

#
# PR Review v2 - pr_review + fetch PR head ref + list changed files vs origin/master
#
# Requirements:
# 1) Identical to pr_review for the first 2 steps (parsing URL + setting up repository)
# 2) git fetch origin refs/pull/<PR>/head:pr-<PR>
# 3) git diff --name-only origin/master...pr-<PR>
#
# IMPORTANT: The pr-<PR> branch must be fetched from the repo identified by the input URL.
# We enforce this by setting origin's URL to the parsed repo_url before fetching.
#
pr_review_v2() {
    local pr_url="$1"
    local mode="${2:-}"
    local print_cd=false
    local quiet=false

    # Same "print-cd" behavior as pr_review for command invocation.
    if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
        if [ -z "$mode" ] || [ "$mode" = "--print-cd" ]; then
            print_cd=true
            quiet=true
        fi
    fi

    if [ "$quiet" = true ]; then
        exec 3>&1
        exec 1>&2
    fi

    if [ -z "$pr_url" ]; then
        print_error "❌ No PR URL specified"
        print_info "💡 Usage: gu pr_review_v2 <url> [--no-print-cd]"
        print_info "💡 Example:"
        print_info "   • gu pr_review_v2 https://github.com/owner/repo/pull/123"
        print_info "   • gu pr_review_v2 https://github.com/owner/repo/compare/feature/security-readme"
        if [ "$quiet" = true ]; then
            exec 1>&3
            exec 3>&-
        fi
        return 1
    fi

    echo ""
    print_info "🔍 PR REVIEW V2 OPERATION"
    echo ""

    # Step 0: Change to reviews directory (same as pr_review)
    print_info "📁 Step 0: Setting up review environment"
    local reviews_dir="${REVIEWS_DIR:-/Users/thomaschang/Documents/dev/git/reviews}"
    if [ ! -d "$reviews_dir" ]; then
        print_info "Creating reviews directory: $reviews_dir"
        mkdir -p "$reviews_dir"
    fi
    print_info "Changing to reviews directory: $reviews_dir"
    cd "$reviews_dir" || return 1
    print_status "✅ Now in reviews directory: $(pwd)"
    echo ""

    # Step 1: Extract PR number or branch and repository info
    print_info "📋 Step 1: Parsing PR or compare URL"
    local clean_url
    clean_url=$(echo "$pr_url" | sed 's/^@//')
    print_info "🔧 Cleaned URL: $clean_url"

    local pr_number=""
    local branch_name=""
    local repo_url=""
    local url_type=""   # "pull" or "compare"

    if echo "$clean_url" | grep -q "/pull/"; then
        print_info "🔍 Detected: Pull Request URL (/pull/<num>)"
        url_type="pull"
        pr_number=$(echo "$clean_url" | grep -o '/pull/[0-9]\+' | grep -o '[0-9]\+')
        repo_url=$(echo "$clean_url" | sed 's|/pull/[0-9][0-9]*.*||')
    elif echo "$clean_url" | grep -q "/compare/"; then
        print_info "🔍 Detected: Compare URL (/compare/<branch>)"
        url_type="compare"
        repo_url=$(echo "$clean_url" | sed 's|/compare/.*||')
        # Branch: part after /compare/; if "base...head" use head
        branch_name=$(echo "$clean_url" | sed 's|.*/compare/||' | sed 's/^[[:space:]]*//;s/[[:space:]]*$//')
        if echo "$branch_name" | grep -q '\.\.\.'; then
            branch_name=$(echo "$branch_name" | sed 's/.*\.\.\.//')
        fi
        if [ -z "$branch_name" ]; then
            print_error "❌ Could not extract branch from compare URL"
            if [ "$quiet" = true ]; then
                exec 1>&3
                exec 3>&-
            fi
            return 1
        fi
    else
        print_error "❌ pr_review_v2 expects a Pull Request URL (/pull/<num>) or Compare URL (/compare/<branch>)"
        print_info "💡 Example PR:   gu pr_review_v2 https://github.com/owner/repo/pull/123"
        print_info "💡 Example compare: gu pr_review_v2 https://github.com/owner/repo/compare/feature/security-readme"
        if [ "$quiet" = true ]; then
            exec 1>&3
            exec 3>&-
        fi
        return 1
    fi

    print_info "🔧 Extracted repository URL: $repo_url"

    # Convert HTTPS URL to SSH format for better authentication (same as pr_review)
    if [[ "$repo_url" =~ ^https://git\.soma\.salesforce\.com/ ]]; then
        repo_url=$(echo "$repo_url" | sed 's|https://git.soma.salesforce.com/|git@git.soma.salesforce.com:|')
        print_info "🔄 Converted to SSH format: $repo_url"
    fi
    if [[ "$repo_url" =~ ^git@git\.soma\.salesforce\.com: ]] && [[ "$repo_url" != *.git ]]; then
        repo_url="${repo_url}.git"
        print_info "🔄 Normalized SSH repo URL (added .git): $repo_url"
    fi

    if [ "$url_type" = "pull" ] && [ -z "$pr_number" ]; then
        print_error "❌ Could not extract PR number from URL"
        if [ "$quiet" = true ]; then
            exec 1>&3
            exec 3>&-
        fi
        return 1
    fi

    if [ "$url_type" = "pull" ]; then
        print_info "✅ PR Number: $pr_number"
    else
        print_info "✅ Branch: $branch_name"
    fi
    print_info "✅ Repository: $repo_url"
    echo ""

    # Step 2: Clone/update the repo
    print_info "📥 Step 2: Setting up repository"
    local clone_dir
    local pr_branch
    local fetch_cmd
    local switch_cmd
    local diff_ref    # ref to compare against base (e.g. origin/master...pr_branch)

    if [ "$url_type" = "pull" ]; then
        clone_dir="pr-review-$pr_number"
        pr_branch="pr-${pr_number}"
        fetch_cmd="git fetch origin \"refs/pull/${pr_number}/head:${pr_branch}\""
        switch_cmd="git switch \"${pr_branch}\""
        diff_ref="origin/master...\"${pr_branch}\""
    else
        # Sanitize branch for directory name: replace / with -
        clone_dir="pr-review-branch-$(echo "$branch_name" | sed 's|/|-|g')"
        pr_branch="$branch_name"
        fetch_cmd="git fetch origin \"${branch_name}\""
        switch_cmd="git switch \"${branch_name}\""
        diff_ref="origin/master...HEAD"
    fi

    if [ ! -d "$clone_dir" ]; then
        print_info "Cloning repository to $clone_dir..."
        print_info "🔧 Repository URL: $repo_url"
        if ! git clone "$repo_url" "$clone_dir"; then
            print_error "❌ Failed to clone repository"
            if [ "$quiet" = true ]; then
                exec 1>&3
                exec 3>&-
            fi
            return 1
        fi
        print_status "✅ Repository cloned successfully"
    else
        print_info "Repository already exists, updating..."
        cd "$clone_dir" || return 1
        git fetch origin
        cd .. || return 1
    fi
    echo ""

    local repo_path="${reviews_dir}/${clone_dir}"

    # If running as a command in print-cd mode: emit a single command suitable for eval.
    if [ "${BASH_SOURCE[0]}" = "${0}" ] && [ "$print_cd" = true ]; then
        exec 1>&3
        echo "cd \"${repo_path}\" && git remote set-url origin \"${repo_url}\" && ${fetch_cmd} && ${switch_cmd} && git diff --name-only ${diff_ref} && ln -s \"\$DIR_AI_TOOLS\" ."
        exec 3>&-
        return 0
    fi

    # Step 3: cd into the cloned directory (same as pr_review behavior when sourced)
    print_info "📂 Step 3: Entering repository directory"
    if [ "${BASH_SOURCE[0]}" != "${0}" ]; then
        if ! cd "$repo_path"; then
            print_error "❌ Failed to cd into: $repo_path"
            if [ "$quiet" = true ]; then
                exec 1>&3
                exec 3>&-
            fi
            return 1
        fi
        print_status "✅ Now in: $(pwd)"
    else
        print_warning "⚠️  This script is running as a command, so it can't cd your current terminal."
        print_info "💡 Do this next:"
        echo "   cd \"$repo_path\""
        echo ""
        print_info "💡 Then run these commands (printed for transparency):"
        echo "   git remote set-url origin \"${repo_url}\""
        echo "   ${fetch_cmd}"
        echo "   ${switch_cmd}"
        echo "   ln -s \"\$DIR_AI_TOOLS\" ."
        if [ "$quiet" = true ]; then
            exec 1>&3
            exec 3>&-
        fi
        return 0
    fi

    echo ""
    print_info "📥 Step 4: Fetch PR head ref into ${pr_branch} (from input repo URL)"
    # Ensure origin is the repo from the input URL (VERY IMPORTANT requirement)
    git remote set-url origin "$repo_url"
    print_info "🔧 Commands:"
    echo "   ${fetch_cmd}"
    echo "   ${switch_cmd}"
    ${fetch_cmd}
    ${switch_cmd}

    echo ""
    print_info "🧾 Step 5: Files changed vs origin/master (PR UI-style)"
    git diff --name-only origin/master..."${pr_branch}"

    echo ""
    print_status "🎉 PR REVIEW V2 READY"

    if [ "$quiet" = true ]; then
        exec 1>&3
        exec 3>&-
    fi
    return 0
}


# Main script logic
if [ "$1" = "help" ] || [ "$1" = "--help" ]; then
    show_help
    exit 0
elif [ "$1" = "functions" ] || [ "$1" = "--functions" ]; then
    show_functions
    exit 0
elif [ "$1" = "status" ] || [ "$1" = "--status" ]; then
    status_check
    exit 0
elif [ "$1" = "new_branch" ] || [ "$1" = "new-branch" ] || [ "$1" = "--new-branch" ]; then
    new_branch
    exit 0
elif [ "$1" = "rebase" ]; then
    rebase
    exit 0
elif [ "$1" = "push_upstream" ] || [ "$1" = "push-upstream" ]; then
    push_upstream
    exit 0
elif [ "$1" = "pr_review" ] || [ "$1" = "pr-review" ]; then
    pr_review "$2" "$3"
    exit 0
elif [ "$1" = "pr_review_v2" ] || [ "$1" = "pr-review-v2" ]; then
    pr_review_v2 "$2" "$3"
    exit 0
else
    # If sourced, don't run main function
    if [ "${BASH_SOURCE[0]}" = "${0}" ]; then
        print_error "Unknown command: $1"
        print_info "Use 'gu help' to see available commands"
        exit 1
    fi
fi
