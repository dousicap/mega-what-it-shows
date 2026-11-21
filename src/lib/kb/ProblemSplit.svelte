<script lang="ts">
  import reports from '#lib/data/reports-4471.json';
  import notes from '#lib/data/desk-notes.json';
  import { groupByCause, readAs, uniqueById, type Report } from '#lib/kb/causes';
  import { tenantOf } from '#lib/kb/locales';

  // One row per problem merged into the ticket, counted the desk's way (causes.ts). A one-day move
  // (desk-notes.json) stays filed under its tenant's cause and also gets its own row.
  let { ticket, issues }: { ticket: number; issues: Record<string, string> } = $props();

  const merged = $derived(uniqueById(reports as Report[]).filter((r) => r.mergedInto === ticket));
  const groups = $derived(groupByCause(merged, tenantOf));
  const moved = $derived(merged.filter((r) => notes.oneDayMove.includes(r.id)));
  const rows = $derived([
    ...groups.map((g) => ({ problem: g.cause as string, reports: g.reports.length, tenants: g.tenants })),
    ...(moved.length ? [{ problem: 'one-day-move', reports: moved.length, tenants: new Set(moved.map((r) => r.tenant)).size }] : []),
  ]);
</script>

<p class="sum">
  <strong>{merged.length}</strong> reports merged into #{ticket} ·
  <strong>{rows.length}</strong>
  {rows.length === 1 ? 'problem' : 'problems'}
</p>

<table>
  <thead>
    <tr><th>problem</th><th>reports</th><th>tenants</th><th>ticket</th></tr>
  </thead>
  <tbody>
    {#each rows as row (row.problem)}
      <tr>
        <td><code>{row.problem}</code></td>
        <td>{row.reports}</td>
        <td>{row.tenants}</td>
        <td>{#if issues[row.problem]}<a href={issues[row.problem]}>#{issues[row.problem].split('/').pop()}</a>{:else}no ticket{/if}</td>
      </tr>
    {/each}
  </tbody>
</table>

{#each groups as g (g.cause)}
  {@const n = readAs(g, notes.oneDayMove)}
  {#if n}
    <p class="note">{n} of the <code>{g.cause}</code> reports read as a one-day move: filed under <code>{g.cause}</code> by tenant, and counted again in <code>one-day-move</code>.</p>
  {/if}
{/each}

<style>
  .sum { font-size: 1.1rem; }
  .note { color: var(--muted); font-size: 0.85em; }
</style>
