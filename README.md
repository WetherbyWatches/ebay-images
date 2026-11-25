# ebay-images

Auto-updating images for Wetherby Watches eBay listings, served by GitHub Pages at
https://wetherbywatches.github.io/ebay-images/

| File | Shown in the listing |
|---|---|
| `thumb-1.jpg` … `thumb-6.jpg` | header strip – newest six listings |
| `feedback.png` | eBay feedback panel |
| `card-1.jpg` … `card-6.jpg` | featured listings – newest six, photo, title, price |

File names never change, so listings that point at them always show the latest version.
`job/` holds the two scripts that redraw them from the public eBay feedback page and eBay shop
(no passwords or keys). `.github/workflows/refresh.yml` runs them every morning and commits the new images.
