// ExercisePicker - searchable list of seeded exercises grouped by muscle group.

import { useEffect, useState } from 'react';
import { listExercises } from '../../api/exercises.js';

export default function ExercisePicker({ onPick, onClose }) {
  const [exercises, setExercises] = useState([]);
  const [query, setQuery] = useState('');

  useEffect(() => {
    // TODO: fetch once on mount; cache in context if needed.
    listExercises().then(setExercises).catch(() => setExercises([]));
  }, []);

  // TODO: derive filtered list by query (case-insensitive on name/muscle_group).

  return (
    <div className="exercise-picker">
      <input
        type="search"
        placeholder="Search exercise..."
        value={query}
        onChange={(e) => setQuery(e.target.value)}
      />
      <ul>
        {/* TODO: render grouped list of exercises */}
      </ul>
    </div>
  );
}
