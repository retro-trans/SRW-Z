"""Regression tests; integration fixtures are private build snapshots."""
import json
import os
import struct
import unittest
from pathlib import Path
from elf import ElfPort,BASE,CAVE,CAVE_FILE,DELTA
from subtitles import native_layout,at


class SubtitleFormatTests(unittest.TestCase):
    def test_header_count_bounds_index_and_preserves_tail(self):
        # Two indexed captions, followed by an unindexed quote-like tail.
        head=struct.pack('<4H',0x4F00,0,2,2)
        pool=b'"One"\0"Two"\0';tail=b'"Not indexed"\0'
        raw=head+struct.pack('<4I',101,0,202,6)+pool+tail
        p,rows,end=native_layout(raw)
        self.assertEqual((p,len(rows),end),(8,2,36))
        self.assertEqual(raw[end:],tail)

    def test_repeated_caption_offsets_are_valid_for_readback(self):
        raw=struct.pack('<4H4I',0x4F00,0,2,2,101,0,202,0)+b'"Same"\0'
        self.assertEqual(at(raw,8,2),[(101,b'"Same"\0'),(202,b'"Same"\0')])

    def test_out_of_bounds_caption_is_rejected(self):
        raw=struct.pack('<4H2I',0x4F00,0,1,1,101,0xFFFF)+b'"One"\0'
        with self.assertRaises(ValueError):at(raw,8,1)


@unittest.skipUnless(os.environ.get('SRWZ_BEST_TEST_WORK'),'Set SRWZ_BEST_TEST_WORK to a private build snapshot')
class RuntimePortTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root=Path(os.environ['SRWZ_BEST_TEST_WORK'])
        cls.layout=json.loads(Path(__file__).with_name('layout.json').read_text(encoding='utf-8'))
        cls.port=ElfPort(cls.root,cls.layout);cls.port.build()

    def test_indexed_font_addresses_move(self):
        for pc,expected in ((0x78B940,0xC160),(0x78C268,0xD0A0),(0x78C2C8,0xC160)):
            off=CAVE_FILE+DELTA+pc-CAVE
            self.assertEqual(struct.unpack_from('<I',self.port.out,off)[0]&65535,expected)

    def test_inline_air_and_size_literals_are_not_pointers(self):
        for hi,lo,value in ((0x389400,0x389404,0x726941),(0x390B40,0x390B48,0x657A69)):
            upper=struct.unpack_from('<I',self.port.out,self.port.map_file(hi-BASE))[0]&65535
            lower=struct.unpack_from('<I',self.port.out,self.port.map_file(lo-BASE))[0]&65535
            self.assertEqual((upper<<16)+lower,value)

    def test_official_code_conflict_stops_build(self):
        port=ElfPort(self.root,self.layout)
        bad=bytearray(port.b);pc=port.map_file(0x13AA68-BASE)
        struct.pack_into('<I',bad,pc,0xFFFFFFFF);port.b=bytes(bad)
        with self.assertRaisesRegex(ValueError,'Official code conflict'):port.build()

    def test_best_native_ending_is_preserved(self):
        rel=Path('DATA/HSFC.BIN/002.bin')
        self.assertEqual((self.root/'decoded/output'/rel).read_bytes(),(self.root/'decoded/best'/rel).read_bytes())

    def test_every_stage_keeps_native_allocation(self):
        for p in (self.root/'decoded/best/DATA/STAGE.BIN').glob('*.bin'):
            out=self.root/'decoded/output/DATA/STAGE.BIN'/p.name
            self.assertEqual(out.stat().st_size,p.stat().st_size,p.name)

    def test_shifted_scenario_names_preserve_native_structure(self):
        import sys
        sys.path.insert(0,os.environ['SRWZ_TOOLS'])
        import stage,fix_stranded_strings as F,fix_struct_intrusions as S
        a,b,c=[(self.root/'decoded'/v/'DATA/STAGE.BIN/161.bin').read_bytes()
               for v in ('original','best','english')]
        out,_=stage.shifted_names_record(a,b,c,F,S)
        self.assertEqual(out[:0x1210],b[:0x1210])
        for owner in (0x62C,0x64C,0x66C,0x68C,0x6AC,0x6CC):
            self.assertEqual(F.text_at(out,stage.u32(out,owner)-stage.BEST),
                             F.text_at(c,stage.u32(c,owner)-stage.BASE))
        bad=bytearray(c);bad[0x100]^=1
        with self.assertRaisesRegex(ValueError,'outside audited name slots'):
            stage.shifted_names_record(a,b,bytes(bad),F,S)


if __name__=='__main__':unittest.main()
