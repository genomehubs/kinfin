use anyhow::{Context, Result};
use std::fs::File;
use std::io::{Seek, SeekFrom, Write};
use std::path::Path;
use std::convert::TryInto;
use memmap2::Mmap;
use std::str;

const MAGIC: &[u8; 8] = b"KFINIDX\0";
const VERSION: u32 = 1;
const HEADER_SIZE: usize = 120; // fixed header size (extended for species entries)

fn align_pos(pos: u64, align: u64) -> u64 {
    if align == 0 { pos }
    else { ((pos + align - 1) / align) * align }
}

#[derive(Debug)]
struct Header {
    pub species_count: u64,
    pub seq_count: u64,
    pub cluster_count: u64,
    pub species_offsets_offset: u64,
    pub species_bytes_offset: u64,
    pub seq_species_offset: u64,
    pub seq_len_offset: u64,
    pub cluster_id_offsets_offset: u64,
    pub cluster_id_bytes_offset: u64,
    pub cluster_members_offsets_offset: u64,
    pub members_offset: u64,
    pub cluster_species_entries_offsets_offset: u64,
    pub cluster_species_entries_bytes_offset: u64,
}

pub fn save_memmap(index: &crate::Index, path: &Path) -> Result<()> {
    // prepare byte blobs and offsets
    let species_count = index.species.len() as u64;
    let seq_count = index.seq_species.len() as u64;
    let cluster_count = index.clusters.len() as u64;

    // species bytes and relative offsets
    let mut species_bytes: Vec<u8> = Vec::new();
    let mut species_rel_offsets: Vec<u64> = Vec::with_capacity(index.species.len() + 1);
    species_rel_offsets.push(0);
    for s in &index.species {
        species_bytes.extend_from_slice(s.as_bytes());
        species_rel_offsets.push(species_bytes.len() as u64);
    }

    // seq_species and seq_len sizes
    let seq_species_len = seq_count as usize * 4;
    let seq_len_len = seq_count as usize * 4;

    // cluster ids bytes + offsets
    let mut cluster_id_bytes: Vec<u8> = Vec::new();
    let mut cluster_id_rel_offsets: Vec<u64> = Vec::with_capacity(index.clusters.len() + 1);
    cluster_id_rel_offsets.push(0);
    for c in &index.clusters {
        cluster_id_bytes.extend_from_slice(c.id.as_bytes());
        cluster_id_rel_offsets.push(cluster_id_bytes.len() as u64);
    }

    // flattened members and cluster member offsets
    let mut flattened_members: Vec<u32> = Vec::new();
    let mut cluster_members_rel_offsets: Vec<u64> = Vec::with_capacity(index.clusters.len() + 1);
    cluster_members_rel_offsets.push(0);

    // per-cluster species entries (for fast aggregation): each entry is
    // species_idx:u32, rel_off:u32 (relative to cluster start), count:u32,
    // count_with_len:u32, sum_len:u64, sumsq_len:u64  --> 32 bytes per entry
    let mut species_entries_bytes: Vec<u8> = Vec::new();
    let mut cluster_species_entries_rel_offsets: Vec<u64> = Vec::with_capacity(index.clusters.len() + 1);
    cluster_species_entries_rel_offsets.push(0);

    for c in &index.clusters {
        // map species -> list of members for this cluster
        let mut species_map: std::collections::HashMap<u32, Vec<u32>> = std::collections::HashMap::new();
        for &m in &c.members {
            let s_idx = index.seq_species[m as usize];
            species_map.entry(s_idx).or_insert_with(Vec::new).push(m);
        }
        // sort species keys for stable layout
        let mut species_keys: Vec<u32> = species_map.keys().copied().collect();
        species_keys.sort_unstable();

        let mut cluster_member_count: u32 = 0;
        for s_idx in species_keys.iter() {
            let members_vec = species_map.get(s_idx).unwrap();
            let rel_off = cluster_member_count;
            let count = members_vec.len() as u32;
            let mut count_with_len: u32 = 0;

            // compute sum and sumsq for lengths
            let mut sum: u64 = 0;
            let mut sumsq: u128 = 0;
            for &mem in members_vec.iter() {
                if let Some(len) = index.seq_len[mem as usize] {
                    sum += len as u64;
                    sumsq += (len as u128) * (len as u128);
                    count_with_len += 1;
                }
            }

            // append members in species-grouped order
            for &mem in members_vec.iter() {
                flattened_members.push(mem);
                cluster_member_count += 1;
            }

            // write species entry: species_idx(u32), rel_off(u32), count(u32), sum(u64), sumsq(u64)
            species_entries_bytes.extend_from_slice(&s_idx.to_le_bytes());
            species_entries_bytes.extend_from_slice(&rel_off.to_le_bytes());
            species_entries_bytes.extend_from_slice(&count.to_le_bytes());
            species_entries_bytes.extend_from_slice(&count_with_len.to_le_bytes());
            species_entries_bytes.extend_from_slice(&sum.to_le_bytes());
            // store lower 64 bits of sumsq (assume fits)
            let sumsq64 = (sumsq as u64).to_le_bytes();
            species_entries_bytes.extend_from_slice(&sumsq64);
        }

        cluster_members_rel_offsets.push(flattened_members.len() as u64);
        cluster_species_entries_rel_offsets.push(species_entries_bytes.len() as u64);
    }

    // compute sizes
    let species_offsets_bytes_len = (species_count as usize + 1) * 8;
    let species_bytes_len = species_bytes.len() as u64;
    let cluster_id_offsets_bytes_len = (cluster_count as usize + 1) * 8;
    let cluster_id_bytes_len = cluster_id_bytes.len() as u64;
    let cluster_members_offsets_bytes_len = (cluster_count as usize + 1) * 8;
    let members_bytes_len = (flattened_members.len() as u64) * 4;
    let cluster_species_entries_offsets_bytes_len = (cluster_count as usize + 1) * 8;
    let cluster_species_entries_bytes_len = species_entries_bytes.len() as u64;

    // compute absolute offsets sequentially
    let mut pos = HEADER_SIZE as u64;
    pos = align_pos(pos, 8);
    let species_offsets_offset = pos;
    pos += species_offsets_bytes_len as u64;
    pos = align_pos(pos, 8);
    let species_bytes_offset = pos;
    pos += species_bytes_len;
    pos = align_pos(pos, 8);
    let seq_species_offset = pos;
    pos += seq_species_len as u64;
    pos = align_pos(pos, 8);
    let seq_len_offset = pos;
    pos += seq_len_len as u64;
    pos = align_pos(pos, 8);
    let cluster_id_offsets_offset = pos;
    pos += cluster_id_offsets_bytes_len as u64;
    pos = align_pos(pos, 8);
    let cluster_id_bytes_offset = pos;
    pos += cluster_id_bytes_len;
    pos = align_pos(pos, 8);
    let cluster_members_offsets_offset = pos;
    pos += cluster_members_offsets_bytes_len as u64;
    pos = align_pos(pos, 8);
    let members_offset = pos;
    pos += members_bytes_len;
    pos = align_pos(pos, 8);
    let cluster_species_entries_offsets_offset = pos;
    pos += cluster_species_entries_offsets_bytes_len as u64;
    pos = align_pos(pos, 8);
    let cluster_species_entries_bytes_offset = pos;
    pos += cluster_species_entries_bytes_len;
    pos = align_pos(pos, 8);

    let file_size = pos;

    // write file
    let mut f = File::create(path).with_context(|| format!("create {}", path.display()))?;
    f.set_len(file_size)?;

    // write header
    f.seek(SeekFrom::Start(0))?;
    // magic
    f.write_all(MAGIC)?;
    // version
    f.write_all(&VERSION.to_le_bytes())?;
    // reserved
    f.write_all(&0u32.to_le_bytes())?;
    // counts
    f.write_all(&species_count.to_le_bytes())?;
    f.write_all(&seq_count.to_le_bytes())?;
    f.write_all(&cluster_count.to_le_bytes())?;
    // offsets
    f.write_all(&species_offsets_offset.to_le_bytes())?;
    f.write_all(&species_bytes_offset.to_le_bytes())?;
    f.write_all(&seq_species_offset.to_le_bytes())?;
    f.write_all(&seq_len_offset.to_le_bytes())?;
    f.write_all(&cluster_id_offsets_offset.to_le_bytes())?;
    f.write_all(&cluster_id_bytes_offset.to_le_bytes())?;
    f.write_all(&cluster_members_offsets_offset.to_le_bytes())?;
    f.write_all(&members_offset.to_le_bytes())?;
    f.write_all(&cluster_species_entries_offsets_offset.to_le_bytes())?;
    f.write_all(&cluster_species_entries_bytes_offset.to_le_bytes())?;

    // write species offsets (absolute offsets into file for each species string start)
    f.seek(SeekFrom::Start(species_offsets_offset))?;
    for rel in &species_rel_offsets {
        let abs = species_bytes_offset + rel;
        f.write_all(&abs.to_le_bytes())?;
    }

    // write species bytes
    f.seek(SeekFrom::Start(species_bytes_offset))?;
    f.write_all(&species_bytes)?;

    // write seq_species array (u32 little endian)
    f.seek(SeekFrom::Start(seq_species_offset))?;
    for &s in &index.seq_species {
        f.write_all(&s.to_le_bytes())?;
    }

    // write seq_len array (u32 little endian), None -> u32::MAX
    f.seek(SeekFrom::Start(seq_len_offset))?;
    for opt in &index.seq_len {
        let out = match opt { Some(v) => *v, None => u32::MAX };
        f.write_all(&out.to_le_bytes())?;
    }

    // write cluster id offsets
    f.seek(SeekFrom::Start(cluster_id_offsets_offset))?;
    for rel in &cluster_id_rel_offsets {
        let abs = cluster_id_bytes_offset + rel;
        f.write_all(&abs.to_le_bytes())?;
    }

    // write cluster id bytes
    f.seek(SeekFrom::Start(cluster_id_bytes_offset))?;
    f.write_all(&cluster_id_bytes)?;

    // write cluster members offsets
    f.seek(SeekFrom::Start(cluster_members_offsets_offset))?;
    for rel in &cluster_members_rel_offsets {
        let abs = members_offset + rel * 4; // each member is u32 (4 bytes)
        f.write_all(&abs.to_le_bytes())?;
    }

    // write flattened members
    f.seek(SeekFrom::Start(members_offset))?;
    for &m in &flattened_members {
        f.write_all(&m.to_le_bytes())?;
    }

    // write cluster species entries offsets
    f.seek(SeekFrom::Start(cluster_species_entries_offsets_offset))?;
    for rel in &cluster_species_entries_rel_offsets {
        let abs = cluster_species_entries_bytes_offset + rel;
        f.write_all(&abs.to_le_bytes())?;
    }

    // write species entries bytes
    f.seek(SeekFrom::Start(cluster_species_entries_bytes_offset))?;
    f.write_all(&species_entries_bytes)?;

    Ok(())
}

pub struct MemmapIndex {
    mmap: Mmap,
    header: Header,
}

impl MemmapIndex {
    pub fn open(path: &Path) -> Result<MemmapIndex> {
        let f = File::open(path)?;
        let mmap = unsafe { Mmap::map(&f)? };
        if mmap.len() < HEADER_SIZE {
            anyhow::bail!("file too small to be an index");
        }
        // parse header
        let magic = &mmap[0..8];
        if magic != MAGIC {
            anyhow::bail!("bad magic");
        }
        let version = u32::from_le_bytes(mmap[8..12].try_into().unwrap());
        if version != VERSION {
            anyhow::bail!("unsupported version {}", version);
        }
        let species_count = u64::from_le_bytes(mmap[16..24].try_into().unwrap());
        let seq_count = u64::from_le_bytes(mmap[24..32].try_into().unwrap());
        let cluster_count = u64::from_le_bytes(mmap[32..40].try_into().unwrap());
        let species_offsets_offset = u64::from_le_bytes(mmap[40..48].try_into().unwrap());
        let species_bytes_offset = u64::from_le_bytes(mmap[48..56].try_into().unwrap());
        let seq_species_offset = u64::from_le_bytes(mmap[56..64].try_into().unwrap());
        let seq_len_offset = u64::from_le_bytes(mmap[64..72].try_into().unwrap());
        let cluster_id_offsets_offset = u64::from_le_bytes(mmap[72..80].try_into().unwrap());
        let cluster_id_bytes_offset = u64::from_le_bytes(mmap[80..88].try_into().unwrap());
        let cluster_members_offsets_offset = u64::from_le_bytes(mmap[88..96].try_into().unwrap());
        let members_offset = u64::from_le_bytes(mmap[96..104].try_into().unwrap());
        let cluster_species_entries_offsets_offset = u64::from_le_bytes(mmap[104..112].try_into().unwrap());
        let cluster_species_entries_bytes_offset = u64::from_le_bytes(mmap[112..120].try_into().unwrap());

        let header = Header {
            species_count,
            seq_count,
            cluster_count,
            species_offsets_offset,
            species_bytes_offset,
            seq_species_offset,
            seq_len_offset,
            cluster_id_offsets_offset,
            cluster_id_bytes_offset,
            cluster_members_offsets_offset,
            members_offset,
            cluster_species_entries_offsets_offset,
            cluster_species_entries_bytes_offset,
        };

        Ok(MemmapIndex { mmap, header })
    }

    pub fn species_count(&self) -> usize { self.header.species_count as usize }
    pub fn seq_count(&self) -> usize { self.header.seq_count as usize }
    pub fn cluster_count(&self) -> usize { self.header.cluster_count as usize }

    pub fn species_name(&self, i: usize) -> Result<String> {
        let sc = self.species_count();
        if i >= sc { anyhow::bail!("out of range"); }
        let off0 = self.read_u64_at(self.header.species_offsets_offset, i)? as usize;
        let off1 = self.read_u64_at(self.header.species_offsets_offset, i+1)? as usize;
        let b = &self.mmap[off0..off1];
        let s = str::from_utf8(b)?.to_string();
        Ok(s)
    }

    fn read_u64_at(&self, base: u64, idx: usize) -> Result<u64> {
        let start = base as usize + idx * 8;
        let end = start + 8;
        let v = u64::from_le_bytes(self.mmap[start..end].try_into().unwrap());
        Ok(v)
    }

    pub fn seq_species_slice(&self) -> Result<&[u32]> {
        let start = self.header.seq_species_offset as usize;
        let len = (self.header.seq_count as usize);
        let end = start + len * 4;
        let slice = &self.mmap[start..end];
        // safety: data is aligned to 8 bytes by writer, so casting is safe
        let arr = bytemuck::try_cast_slice(slice).map_err(|_| anyhow::anyhow!("cast seq_species failed"))?;
        Ok(arr)
    }

    pub fn seq_len_raw_slice(&self) -> Result<&[u32]> {
        let start = self.header.seq_len_offset as usize;
        let len = (self.header.seq_count as usize);
        let end = start + len * 4;
        let slice = &self.mmap[start..end];
        let arr = bytemuck::try_cast_slice(slice).map_err(|_| anyhow::anyhow!("cast seq_len failed"))?;
        Ok(arr)
    }

    pub fn cluster_members_for(&self, cluster_idx: usize) -> Result<&[u32]> {
        if cluster_idx >= self.cluster_count() { anyhow::bail!("cluster idx OOB"); }
        let start_abs = self.read_u64_at(self.header.cluster_members_offsets_offset, cluster_idx)? as usize;
        let end_abs = self.read_u64_at(self.header.cluster_members_offsets_offset, cluster_idx+1)? as usize;
        let start = start_abs;
        let end = end_abs;
        if end < start { anyhow::bail!("bad offsets"); }
        let slice = &self.mmap[start..end];
        let arr = bytemuck::try_cast_slice(slice).map_err(|_| anyhow::anyhow!("cast members failed"))?;
        Ok(arr)
    }

    pub fn cluster_species_entries_bytes_for(&self, cluster_idx: usize) -> Result<&[u8]> {
        if cluster_idx >= self.cluster_count() { anyhow::bail!("cluster idx OOB"); }
        let start_abs = self.read_u64_at(self.header.cluster_species_entries_offsets_offset, cluster_idx)? as usize;
        let end_abs = self.read_u64_at(self.header.cluster_species_entries_offsets_offset, cluster_idx+1)? as usize;
        if end_abs < start_abs { anyhow::bail!("bad species entries offsets"); }
        let slice = &self.mmap[start_abs..end_abs];
        Ok(slice)
    }
}
