# Component Patterns

## Card

Container for grouped content.

```html
<div class="bg-white rounded-lg border border-gray-200 p-6">
  <h3 class="font-semibold mb-3">Title</h3>
  <!-- content -->
</div>
```

## Metric Card

Numeric KPI display in a grid.

```html
<div class="bg-white rounded-lg border border-gray-200 p-4 text-center">
  <div class="text-2xl font-bold text-primary-600">{{ value }}</div>
  <div class="text-xs text-gray-500 mt-1">{{ label }}</div>
</div>
```

Grid: `grid grid-cols-5 gap-4` (adjust cols as needed)

## Status Banner

Contextual alert at top of page.

```html
<!-- Success -->
<div class="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
  <h2 class="text-xl font-bold text-green-800">{{ message }}</h2>
</div>

<!-- Error -->
<div class="bg-red-50 border border-red-200 rounded-lg p-4 mb-6">
  <h4 class="font-medium text-red-800 mb-2">Errors</h4>
  {% for e in errors %}<div class="text-sm text-red-700">{{ e }}</div>{% endfor %}
</div>

<!-- Warning -->
<div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4 mb-6">
  <p class="text-yellow-800">{{ message }}</p>
</div>

<!-- Info -->
<div class="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4 text-sm">
  <div class="text-blue-800">{{ message }}</div>
</div>
```

## Progress Indicator

For running pipeline states.

```html
<div class="bg-white rounded-lg border border-gray-200 p-4 mb-4">
  <div class="flex items-center gap-3 mb-2">
    <div class="animate-spin h-5 w-5 border-2 border-primary-600 border-t-transparent rounded-full"></div>
    <span class="font-medium text-sm" x-text="currentStep">Starting...</span>
  </div>
  <div class="w-full bg-gray-200 rounded-full h-1.5">
    <div class="bg-primary-600 h-1.5 rounded-full transition-all" :style="'width:' + progress + '%'"></div>
  </div>
</div>
```

## Log Viewer (Terminal)

Real-time log output.

```html
<div class="bg-dark-900 rounded-lg p-4 font-mono text-xs text-green-400 h-96 overflow-y-auto" id="log-container">
  <template x-for="(line, i) in logs" :key="i">
    <div x-text="line"></div>
  </template>
</div>
```

## Tabs (Alpine.js)

Tab navigation within a card.

```html
<div x-data="{ activeTab: 'first' }">
  <div class="flex border-b border-gray-200">
    <button @click="activeTab='first'"
            :class="activeTab==='first' ? 'border-primary-600 text-primary-600' : 'border-transparent text-gray-500'"
            class="px-4 py-3 text-sm font-medium border-b-2 whitespace-nowrap transition">
      First
    </button>
    <!-- more tabs -->
  </div>
  <div class="p-6">
    <div x-show="activeTab==='first'">Content</div>
    <div x-show="activeTab==='second'" x-cloak>Content</div>
  </div>
</div>
```

## Collapsible Section

```html
<details class="bg-white rounded-lg border border-gray-200">
  <summary class="px-4 py-3 cursor-pointer text-sm font-medium">Title</summary>
  <div class="px-4 pb-4">Content</div>
</details>
```

## Code File Viewer

For displaying generated source code files.

```html
<details class="mb-3 border border-gray-200 rounded">
  <summary class="px-3 py-2 bg-gray-50 cursor-pointer text-sm font-mono">{{ filepath }}</summary>
  <pre class="p-3 text-xs overflow-auto max-h-80">{{ content }}</pre>
</details>
```

## Button Styles

```html
<!-- Primary -->
<button class="px-6 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 transition font-medium">
  Action
</button>

<!-- Secondary -->
<button class="px-4 py-2 bg-white border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition text-sm font-medium">
  Secondary
</button>

<!-- Text link -->
<a class="px-4 py-2 text-gray-500 hover:text-gray-700 transition text-sm">Cancel</a>
```

## Form Elements

```html
<!-- Text input -->
<input type="text" name="field"
       class="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-transparent outline-none">

<!-- Select -->
<select class="w-full px-4 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-primary-500">
  <option>Choice</option>
</select>

<!-- Textarea -->
<textarea rows="8"
          class="w-full px-4 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-primary-500 resize-y"></textarea>
```

## Progress Bar (Static)

```html
<div class="mb-2">
  <div class="flex justify-between text-sm mb-1">
    <span>{{ label }}</span>
    <span class="text-gray-500">{{ value }} ({{ pct }}%)</span>
  </div>
  <div class="w-full bg-gray-200 rounded-full h-2">
    <div class="bg-primary-500 h-2 rounded-full" style="width:{{ pct }}%"></div>
  </div>
</div>
```

## Action Bar

Horizontal layout for approve/reject/cancel.

```html
<div class="flex items-start gap-4">
  <!-- Primary action form -->
  <form method="post" action="/api/...">
    <button type="submit" class="px-6 py-2 bg-primary-600 text-white rounded-lg ...">Approve</button>
  </form>
  <!-- Secondary action with input -->
  <form method="post" action="/api/..." class="flex gap-2">
    <input type="text" name="feedback" class="...">
    <button type="submit" class="...">Request Changes</button>
  </form>
  <!-- Cancel link -->
  <a href="/" class="...">Cancel</a>
</div>
```
