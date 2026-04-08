Write-Output "Configuring git user..."
git config user.email "bot@antigravity.ai"
git config user.name "Antigravity Assistant"

Write-Output "Resetting index..."
git reset

Write-Output "Adding files..."
git add .

Write-Output "Committing..."
git commit -m "Auto-commit: Scraper project setup (Clean)"

Write-Output "Pushing..."
git push -u origin main
